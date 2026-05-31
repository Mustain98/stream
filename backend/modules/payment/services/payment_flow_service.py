import uuid
from sqlmodel import Session

from models import StreamAccessType, TransactionStatus, Stream
from modules.payment.services.stripe_service import (
    create_stream_checkout_session,
    retrieve_checkout_session,
)
from modules.payment.services.payment_fee_service import (
    calculate_platform_fee,
    calculate_broadcaster_amount,
)
from modules.payment.services.earnings_relay_service import relay_stream_earnings_update
from modules.payment.services.stripe_connect_account_service import (
    get_stripe_connect_account_by_user_id,
)
from modules.payment.services.transaction_service import (
    get_or_create_access_setting,
    has_paid_for_stream,
    create_pending_transaction,
    mark_transaction_checkout_created,
    mark_transaction_paid,
    mark_transaction_failed,
    mark_transaction_cancelled,
    get_transaction,
    get_transaction_by_provider_session,
    set_transaction_provider_session,
    get_latest_checkout_transaction,
    record_stripe_event_processed,
)
from modules.payment.services.stream_payment_settlement_service import stripe_object_to_dict


class PaymentFlowError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)


def validate_stream_pricing(session: Session, stream_id: str):
    setting = get_or_create_access_setting(session, stream_id)
    if setting.access_type == StreamAccessType.FREE:
        raise PaymentFlowError("stream_is_free", "Stream is free")
    if setting.price_amount <= 0:
        raise PaymentFlowError("invalid_price", "Invalid stream price")
    return setting


def validate_broadcaster_stripe_account(session: Session, broadcaster_id: str):
    connect_account = get_stripe_connect_account_by_user_id(session, broadcaster_id)
    if not connect_account or not connect_account.stripe_account_id:
        raise PaymentFlowError("broadcaster_not_connected", "Broadcaster has not connected a Stripe account")
    if not connect_account.onboarding_completed:
        raise PaymentFlowError("broadcaster_onboarding_incomplete", "Broadcaster has not completed Stripe onboarding")
    return connect_account


def calculate_transaction_fees(price_amount: int):
    platform_fee = calculate_platform_fee(price_amount)
    broadcaster_amount = calculate_broadcaster_amount(price_amount, platform_fee)
    return {
        "platform_fee": platform_fee,
        "broadcaster_amount": broadcaster_amount
    }


def handle_existing_checkout(session: Session, stream_id: str, user_id: str):
    existing_checkout = get_latest_checkout_transaction(
        session=session, stream_id=stream_id, user_id=user_id, provider="stripe"
    )
    if not existing_checkout or not existing_checkout.provider_session_id:
        return None

    try:
        old_session = retrieve_checkout_session(existing_checkout.provider_session_id)
        old_session_dict = stripe_object_to_dict(old_session)

        old_status = old_session_dict.get("status")
        old_payment_status = old_session_dict.get("payment_status")
        old_checkout_url = old_session_dict.get("url")
        old_payment_intent_id = old_session_dict.get("payment_intent")

        if old_payment_status == "paid":
            return verify_and_finalize_successful_payment(
                session=session,
                transaction=existing_checkout,
                checkout_session_id=existing_checkout.provider_session_id,
                payment_intent_id=old_payment_intent_id,
                event_id=None,
                event_type="manual_checkout_reuse",
            )

        if old_status == "open" and old_checkout_url:
            return {
                "checkout_url": old_checkout_url,
                "checkout_session_id": existing_checkout.provider_session_id,
                "transaction_id": existing_checkout.id,
                "amount": existing_checkout.amount,
                "currency": existing_checkout.currency,
                "platform_fee_amount": existing_checkout.platform_fee_amount,
                "broadcaster_amount": existing_checkout.broadcaster_amount,
                "broadcaster_id": existing_checkout.broadcaster_id,
            }

        mark_transaction_cancelled(
            session=session,
            transaction=existing_checkout,
            reason=f"old_checkout_unusable:{old_status}:{old_payment_status}",
        )
        session.commit()
    except Exception as e:
        mark_transaction_cancelled(
            session=session,
            transaction=existing_checkout,
            reason=f"old_checkout_retrieve_failed:{str(e)}",
        )
        session.commit()
    return None


def initialize_new_stripe_checkout(session: Session, stream: Stream, user_id: str, setting, connect_account, fees: dict):
    idempotency_key = f"checkout:{stream.id}:{user_id}:{uuid.uuid4()}"

    transaction = create_pending_transaction(
        session=session,
        stream_id=stream.id,
        user_id=user_id,
        broadcaster_id=str(stream.broadcaster_id),
        amount=setting.price_amount,
        currency=setting.currency,
        provider="stripe",
        platform_fee_amount=fees["platform_fee"],
        broadcaster_amount=fees["broadcaster_amount"],
        stripe_transfer_destination=connect_account.stripe_account_id,
        provider_idempotency_key=idempotency_key,
    )
    session.commit()
    session.refresh(transaction)

    try:
        checkout_session = create_stream_checkout_session(
            stream_id=stream.id,
            user_id=user_id,
            broadcaster_id=str(stream.broadcaster_id),
            transaction_id=transaction.id,
            title=stream.title,
            amount=transaction.amount,
            currency=transaction.currency,
            idempotency_key=idempotency_key,
        )
    except Exception as e:
        mark_transaction_failed(session=session, transaction=transaction, reason=f"stripe_checkout_failed:{str(e)}")
        session.commit()
        raise PaymentFlowError("stripe_checkout_failed", "Could not create Stripe checkout session. Please try again.")

    try:
        mark_transaction_checkout_created(session=session, transaction=transaction, provider_session_id=checkout_session.id)
        session.commit()
        session.refresh(transaction)
    except Exception:
        session.rollback()
        raise PaymentFlowError("checkout_state_save_failed", "Checkout was created but local state could not be saved. Please retry.")

    return {
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
        "transaction_id": transaction.id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "platform_fee_amount": transaction.platform_fee_amount,
        "broadcaster_amount": transaction.broadcaster_amount,
        "broadcaster_id": transaction.broadcaster_id,
    }


def verify_and_finalize_successful_payment(
    session: Session, transaction, checkout_session_id: str, payment_intent_id: str, event_id: str | None, event_type: str
):
    if not transaction.provider_session_id:
        set_transaction_provider_session(session=session, transaction=transaction, provider_session_id=checkout_session_id)

    if transaction.status == TransactionStatus.PAID:
        if event_id:
            record_stripe_event_processed(session=session, stripe_event_id=event_id, event_type=event_type, object_id=checkout_session_id)
            session.commit()
        return {"status": "already_paid", "transaction_id": transaction.id, "stream_id": transaction.stream_id}

    mark_transaction_paid(session=session, transaction=transaction, provider_payment_id=payment_intent_id)

    if event_id:
        record_stripe_event_processed(session=session, stripe_event_id=event_id, event_type=event_type, object_id=checkout_session_id)

    session.commit()
    session.refresh(transaction)
    relay_stream_earnings_update(session=session, stream_id=transaction.stream_id)

    return {
        "status": "paid",
        "transaction_id": transaction.id,
        "stream_id": transaction.stream_id,
        "user_id": transaction.user_id,
        "broadcaster_id": transaction.broadcaster_id,
        "amount": transaction.amount,
        "platform_fee_amount": transaction.platform_fee_amount,
        "broadcaster_amount": transaction.broadcaster_amount,
    }


def get_and_validate_checkout_session(session: Session, checkout_session_id: str, user_id: str):
    stripe_session = retrieve_checkout_session(checkout_session_id)
    stripe_session_dict = stripe_object_to_dict(stripe_session)

    payment_intent_id = stripe_session_dict.get("payment_intent")
    metadata = stripe_session_dict.get("metadata") or {}

    if stripe_session_dict.get("payment_status") != "paid":
        raise PaymentFlowError("not_paid", "Session is not paid")

    transaction = get_transaction_by_provider_session(session=session, provider_session_id=checkout_session_id)

    if not transaction and metadata.get("transaction_id"):
        transaction = get_transaction(session, metadata.get("transaction_id"))

    if not transaction:
        raise PaymentFlowError("transaction_not_found", "Transaction not found")

    if str(transaction.user_id) != str(user_id):
        raise PaymentFlowError("not_allowed", "Not allowed")

    if str(metadata.get("transaction_id")) != str(transaction.id) or \
       str(metadata.get("stream_id")) != str(transaction.stream_id) or \
       str(metadata.get("user_id")) != str(transaction.user_id) or \
       str(metadata.get("broadcaster_id")) != str(transaction.broadcaster_id):
        raise PaymentFlowError("metadata_mismatch", "Stripe metadata mismatch")

    return payment_intent_id, transaction
