import os
import uuid

import stripe
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from models import StreamAccessType, TransactionStatus
from services.stream_service import get_stream
from services.stripe_service import (
    create_stream_checkout_session,
    retrieve_checkout_session,
    retrieve_payment_intent,
    create_refund_for_payment_intent,
)
from services.payment_fee_service import (
    calculate_platform_fee,
    calculate_broadcaster_amount,
)
from services.stripe_connect_account_service import (
    get_stripe_connect_account_by_user_id,
)
from services.transaction_service import (
    get_or_create_access_setting,
    has_paid_for_stream,
    create_pending_transaction,
    mark_transaction_checkout_created,
    mark_transaction_paid,
    mark_transaction_failed,
    mark_transaction_cancelled,
    mark_transaction_refund_pending,
    mark_transaction_refunded,
    mark_transaction_refund_failed,
    get_transaction,
    get_transaction_by_provider_session,
    set_transaction_provider_session,
    get_latest_checkout_transaction,
    cancel_stuck_pending_transactions_for_stream_user,
    has_processed_stripe_event,
    record_stripe_event_processed,
)

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


def stripe_object_to_dict(obj):
    if isinstance(obj, dict):
        return obj

    try:
        return obj.to_dict_recursive()
    except AttributeError:
        pass

    try:
        return obj._to_dict_recursive()
    except AttributeError:
        pass

    return dict(obj)


def create_stripe_checkout_controller(
    session: Session,
    stream_id: str,
    user_id: str,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    if str(stream.broadcaster_id) == str(user_id):
        return None, "publisher_cannot_pay"

    setting = get_or_create_access_setting(session, stream_id)

    if setting.access_type == StreamAccessType.FREE:
        session.commit()
        return None, "stream_is_free"

    if setting.price_amount <= 0:
        session.commit()
        return None, "invalid_price"

    connect_account = get_stripe_connect_account_by_user_id(
        session=session,
        user_id=str(stream.broadcaster_id),
    )

    if not connect_account:
        session.commit()
        return None, "broadcaster_not_connected"

    if not connect_account.onboarding_completed:
        session.commit()
        return None, "broadcaster_onboarding_incomplete"

    if not connect_account.stripe_account_id:
        session.commit()
        return None, "broadcaster_not_connected"

    if has_paid_for_stream(session, stream_id, user_id):
        session.commit()
        return {
            "status": "already_paid",
            "stream_id": stream_id,
        }, None

    existing_checkout = get_latest_checkout_transaction(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        provider="stripe",
    )

    if existing_checkout and existing_checkout.provider_session_id:
        try:
            old_session = retrieve_checkout_session(existing_checkout.provider_session_id)
            old_session_dict = stripe_object_to_dict(old_session)

            old_status = old_session_dict.get("status")
            old_payment_status = old_session_dict.get("payment_status")
            old_checkout_url = old_session_dict.get("url")
            old_payment_intent_id = old_session_dict.get("payment_intent")

            print(
                "[Stripe Checkout Reuse]",
                "transaction=", existing_checkout.id,
                "session=", existing_checkout.provider_session_id,
                "status=", old_status,
                "payment_status=", old_payment_status,
            )

            if old_payment_status == "paid":
                result, _ = finalize_paid_transaction_or_refund(
                    session=session,
                    transaction=existing_checkout,
                    checkout_session_id=existing_checkout.provider_session_id,
                    payment_intent_id=old_payment_intent_id,
                    event_id=None,
                    event_type="manual_checkout_reuse",
                )

                return result, None

            if old_status == "open" and old_checkout_url:
                session.commit()

                return {
                    "checkout_url": old_checkout_url,
                    "checkout_session_id": existing_checkout.provider_session_id,
                    "transaction_id": existing_checkout.id,
                    "amount": existing_checkout.amount,
                    "currency": existing_checkout.currency,
                    "platform_fee_amount": existing_checkout.platform_fee_amount,
                    "broadcaster_amount": existing_checkout.broadcaster_amount,
                    "broadcaster_id": existing_checkout.broadcaster_id,
                }, None

            mark_transaction_cancelled(
                session=session,
                transaction=existing_checkout,
                reason=f"old_checkout_unusable:{old_status}:{old_payment_status}",
            )
            session.commit()

        except Exception as e:
            print("[Stripe Checkout Reuse] Could not retrieve old session:", str(e))
            mark_transaction_cancelled(
                session=session,
                transaction=existing_checkout,
                reason=f"old_checkout_retrieve_failed:{str(e)}",
            )
            session.commit()

    cancel_stuck_pending_transactions_for_stream_user(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        provider="stripe",
    )
    session.commit()

    platform_fee_amount = calculate_platform_fee(setting.price_amount)

    broadcaster_amount = calculate_broadcaster_amount(
        amount=setting.price_amount,
        platform_fee_amount=platform_fee_amount,
    )

    idempotency_key = f"checkout:{stream_id}:{user_id}:{uuid.uuid4()}"

    transaction = create_pending_transaction(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        broadcaster_id=str(stream.broadcaster_id),
        amount=setting.price_amount,
        currency=setting.currency,
        provider="stripe",
        platform_fee_amount=platform_fee_amount,
        broadcaster_amount=broadcaster_amount,
        stripe_transfer_destination=connect_account.stripe_account_id,
        provider_idempotency_key=idempotency_key,
    )

    session.commit()
    session.refresh(transaction)

    try:
        checkout_session = create_stream_checkout_session(
            stream_id=stream_id,
            user_id=user_id,
            broadcaster_id=str(stream.broadcaster_id),
            transaction_id=transaction.id,
            title=stream.title,
            amount=transaction.amount,
            currency=transaction.currency,
            broadcaster_stripe_account_id=connect_account.stripe_account_id,
            platform_fee_amount=transaction.platform_fee_amount,
            idempotency_key=idempotency_key,
        )

    except Exception as e:
        mark_transaction_failed(
            session=session,
            transaction=transaction,
            reason=f"stripe_checkout_failed:{str(e)}",
        )
        session.commit()

        print("[Stripe Checkout] Stripe session creation failed:", str(e))
        return None, "stripe_checkout_failed"

    try:
        mark_transaction_checkout_created(
            session=session,
            transaction=transaction,
            provider_session_id=checkout_session.id,
        )

        session.commit()
        session.refresh(transaction)

    except Exception as e:
        session.rollback()
        print("[Stripe Checkout] DB update failed after Stripe success:", str(e))
        return None, "checkout_state_save_failed"

    return {
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
        "transaction_id": transaction.id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "platform_fee_amount": transaction.platform_fee_amount,
        "broadcaster_amount": transaction.broadcaster_amount,
        "broadcaster_id": transaction.broadcaster_id,
    }, None


def verify_broadcaster_transfer(
    payment_intent_id: str,
    expected_destination: str,
):
    """
    Best-effort verification that Stripe created a destination transfer
    for the expected connected account.
    """
    if not payment_intent_id:
        return False, "missing_payment_intent_id"

    if not expected_destination:
        return False, "missing_expected_destination"

    payment_intent = retrieve_payment_intent(payment_intent_id)
    payment_intent_dict = stripe_object_to_dict(payment_intent)

    latest_charge = payment_intent_dict.get("latest_charge")

    if not latest_charge:
        return False, "missing_latest_charge"

    if not isinstance(latest_charge, dict):
        latest_charge = stripe_object_to_dict(latest_charge)

    transfer = latest_charge.get("transfer")
    transfer_data = latest_charge.get("transfer_data")

    destination = None

    if isinstance(transfer, dict):
        destination = transfer.get("destination")
    elif isinstance(transfer, str) and transfer:
        # If only transfer id is returned, destination cannot be verified here.
        # Treat it as inconclusive rather than safe.
        return False, "transfer_not_expanded"

    if not destination and isinstance(transfer_data, dict):
        destination = transfer_data.get("destination")

    if not destination:
        return False, "missing_transfer_destination"

    if str(destination) != str(expected_destination):
        return False, "transfer_destination_mismatch"

    return True, None


def refund_viewer_for_failed_broadcaster_delivery(
    session: Session,
    transaction,
    payment_intent_id: str,
    reason: str,
):
    """
    Payment succeeded at Stripe, but broadcaster delivery cannot be verified.
    Refund the viewer and do not unlock access.
    """
    try:
        mark_transaction_refund_pending(
            session=session,
            transaction=transaction,
            reason=reason,
        )
        session.commit()
        session.refresh(transaction)

        refund = create_refund_for_payment_intent(
            payment_intent_id=payment_intent_id,
            reason="requested_by_customer",
        )

        refund_dict = stripe_object_to_dict(refund)

        mark_transaction_refunded(
            session=session,
            transaction=transaction,
            provider_refund_id=refund_dict.get("id"),
            reason=reason,
        )
        session.commit()
        session.refresh(transaction)

        return {
            "status": "refunded",
            "transaction_id": transaction.id,
            "refund_id": transaction.provider_refund_id,
            "reason": reason,
        }, None

    except Exception as refund_error:
        session.rollback()

        mark_transaction_refund_failed(
            session=session,
            transaction=transaction,
            reason=f"{reason}; refund_error={str(refund_error)}",
        )
        session.commit()
        session.refresh(transaction)

        return {
            "status": "refund_failed",
            "transaction_id": transaction.id,
            "reason": reason,
        }, None


def finalize_paid_transaction_or_refund(
    session: Session,
    transaction,
    checkout_session_id: str,
    payment_intent_id: str,
    event_id: str | None,
    event_type: str,
):
    """
    This is the only place where successful Stripe payment becomes PAID.
    If broadcaster delivery cannot be verified, refund instead.
    """
    if not transaction.provider_session_id:
        set_transaction_provider_session(
            session=session,
            transaction=transaction,
            provider_session_id=checkout_session_id,
        )

    if transaction.status == TransactionStatus.PAID:
        if event_id:
            record_stripe_event_processed(
                session=session,
                stripe_event_id=event_id,
                event_type=event_type,
                object_id=checkout_session_id,
            )
        session.commit()

        return {
            "status": "already_paid",
            "transaction_id": transaction.id,
            "stream_id": transaction.stream_id,
        }, None

    already_paid = has_paid_for_stream(
        session=session,
        stream_id=transaction.stream_id,
        user_id=transaction.user_id,
    )

    if already_paid:
        result, _ = refund_viewer_for_failed_broadcaster_delivery(
            session=session,
            transaction=transaction,
            payment_intent_id=payment_intent_id,
            reason="duplicate_successful_payment_refunded",
        )

        if event_id:
            record_stripe_event_processed(
                session=session,
                stripe_event_id=event_id,
                event_type=event_type,
                object_id=checkout_session_id,
            )
            session.commit()

        return result, None

    if not transaction.stripe_transfer_destination:
        result, _ = refund_viewer_for_failed_broadcaster_delivery(
            session=session,
            transaction=transaction,
            payment_intent_id=payment_intent_id,
            reason="payment_not_delivered_to_broadcaster:missing_transfer_destination",
        )

        if event_id:
            record_stripe_event_processed(
                session=session,
                stripe_event_id=event_id,
                event_type=event_type,
                object_id=checkout_session_id,
            )
            session.commit()

        return result, None

    transfer_ok, transfer_error = verify_broadcaster_transfer(
        payment_intent_id=payment_intent_id,
        expected_destination=transaction.stripe_transfer_destination,
    )

    if not transfer_ok:
        result, _ = refund_viewer_for_failed_broadcaster_delivery(
            session=session,
            transaction=transaction,
            payment_intent_id=payment_intent_id,
            reason=f"payment_not_delivered_to_broadcaster:{transfer_error}",
        )

        if event_id:
            record_stripe_event_processed(
                session=session,
                stripe_event_id=event_id,
                event_type=event_type,
                object_id=checkout_session_id,
            )
            session.commit()

        return result, None

    mark_transaction_paid(
        session=session,
        transaction=transaction,
        provider_payment_id=payment_intent_id,
    )

    if event_id:
        record_stripe_event_processed(
            session=session,
            stripe_event_id=event_id,
            event_type=event_type,
            object_id=checkout_session_id,
        )

    session.commit()
    session.refresh(transaction)

    print("[Stripe] marked transaction paid:", transaction.id)

    return {
        "status": "paid",
        "transaction_id": transaction.id,
        "stream_id": transaction.stream_id,
        "user_id": transaction.user_id,
        "broadcaster_id": transaction.broadcaster_id,
        "amount": transaction.amount,
        "platform_fee_amount": transaction.platform_fee_amount,
        "broadcaster_amount": transaction.broadcaster_amount,
    }, None


async def handle_stripe_webhook_controller(
    request: Request,
    session: Session,
):
    if not STRIPE_WEBHOOK_SECRET:
        return None, "missing_webhook_secret"

    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return None, "invalid_payload"
    except stripe.error.SignatureVerificationError:
        return None, "invalid_signature"

    event_id = event["id"]
    event_type = event["type"]

    event_object = stripe_object_to_dict(event["data"]["object"])
    object_id = event_object.get("id")

    if has_processed_stripe_event(session, event_id):
        return {
            "status": "duplicate_ignored",
            "event_id": event_id,
        }, None

    if event_type != "checkout.session.completed":
        record_stripe_event_processed(
            session=session,
            stripe_event_id=event_id,
            event_type=event_type,
            object_id=object_id,
        )
        session.commit()

        return {
            "status": "ignored",
            "event_type": event_type,
            "object_id": object_id,
        }, None

    checkout_session = event_object

    checkout_session_id = checkout_session.get("id")
    payment_intent_id = checkout_session.get("payment_intent")
    payment_status = checkout_session.get("payment_status")
    metadata = checkout_session.get("metadata") or {}

    print("[Stripe Webhook] checkout.session.completed")
    print("[Stripe Webhook] event_id=", event_id)
    print("[Stripe Webhook] checkout_session_id=", checkout_session_id)
    print("[Stripe Webhook] payment_intent_id=", payment_intent_id)
    print("[Stripe Webhook] payment_status=", payment_status)
    print("[Stripe Webhook] metadata=", metadata)

    if payment_status != "paid":
        record_stripe_event_processed(
            session=session,
            stripe_event_id=event_id,
            event_type=event_type,
            object_id=checkout_session_id,
        )
        session.commit()

        return {
            "status": "ignored",
            "reason": "payment_status_not_paid",
            "payment_status": payment_status,
        }, None

    transaction = get_transaction_by_provider_session(
        session=session,
        provider_session_id=checkout_session_id,
    )

    if not transaction:
        transaction_id = metadata.get("transaction_id")

        if transaction_id:
            transaction = get_transaction(session, transaction_id)

    if not transaction:
        record_stripe_event_processed(
            session=session,
            stripe_event_id=event_id,
            event_type=event_type,
            object_id=checkout_session_id,
        )
        session.commit()

        print("[Stripe Webhook] transaction not found:", checkout_session_id)

        return {
            "status": "ignored",
            "reason": "transaction_not_found",
            "checkout_session_id": checkout_session_id,
        }, None

    if str(metadata.get("transaction_id")) != str(transaction.id):
        return None, "metadata_mismatch"

    if str(metadata.get("stream_id")) != str(transaction.stream_id):
        return None, "metadata_mismatch"

    if str(metadata.get("user_id")) != str(transaction.user_id):
        return None, "metadata_mismatch"

    if str(metadata.get("broadcaster_id")) != str(transaction.broadcaster_id):
        return None, "metadata_mismatch"

    try:
        return finalize_paid_transaction_or_refund(
            session=session,
            transaction=transaction,
            checkout_session_id=checkout_session_id,
            payment_intent_id=payment_intent_id,
            event_id=event_id,
            event_type=event_type,
        )

    except IntegrityError as e:
        session.rollback()

        print("[Stripe Webhook] integrity error:", str(e))

        already_paid_after_rollback = has_paid_for_stream(
            session=session,
            stream_id=transaction.stream_id,
            user_id=transaction.user_id,
        )

        if already_paid_after_rollback:
            return {
                "status": "already_paid",
                "transaction_id": transaction.id,
            }, None

        raise


def reconcile_checkout_session_controller(
    session: Session,
    checkout_session_id: str,
    user_id: str,
):
    stripe_session = retrieve_checkout_session(checkout_session_id)
    stripe_session_dict = stripe_object_to_dict(stripe_session)

    payment_status = stripe_session_dict.get("payment_status")
    payment_intent_id = stripe_session_dict.get("payment_intent")
    metadata = stripe_session_dict.get("metadata") or {}

    if payment_status != "paid":
        return {
            "status": "not_paid",
            "payment_status": payment_status,
        }, None

    transaction = get_transaction_by_provider_session(
        session=session,
        provider_session_id=checkout_session_id,
    )

    if not transaction:
        transaction_id = metadata.get("transaction_id")

        if transaction_id:
            transaction = get_transaction(session, transaction_id)

    if not transaction:
        return None, "transaction_not_found"

    if str(transaction.user_id) != str(user_id):
        return None, "not_allowed"

    if str(metadata.get("transaction_id")) != str(transaction.id):
        return None, "metadata_mismatch"

    if str(metadata.get("stream_id")) != str(transaction.stream_id):
        return None, "metadata_mismatch"

    if str(metadata.get("user_id")) != str(transaction.user_id):
        return None, "metadata_mismatch"

    if str(metadata.get("broadcaster_id")) != str(transaction.broadcaster_id):
        return None, "metadata_mismatch"

    return finalize_paid_transaction_or_refund(
        session=session,
        transaction=transaction,
        checkout_session_id=checkout_session_id,
        payment_intent_id=payment_intent_id,
        event_id=None,
        event_type="manual_reconcile",
    )