import os

import stripe
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from models import StreamAccessType, TransactionStatus
from services.stream_service import get_stream
from services.stripe_service import create_stream_checkout_session
from services.transaction_service import (
    get_or_create_access_setting,
    has_paid_for_stream,
    create_pending_transaction,
    mark_transaction_paid,
    get_transaction_by_provider_session,
    set_transaction_provider_session,
    cancel_pending_transactions_for_stream_user,
    cancel_transaction,
)

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


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

    if has_paid_for_stream(session, stream_id, user_id):
        session.commit()
        return {
            "status": "already_paid",
            "stream_id": stream_id,
        }, None

    # Important:
    # prevent multiple active pending checkout attempts for same viewer + stream.
    cancel_pending_transactions_for_stream_user(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        provider="stripe",
    )

    transaction = create_pending_transaction(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        amount=setting.price_amount,
        currency=setting.currency,
        provider="stripe",
    )

    session.commit()
    session.refresh(transaction)

    checkout_session = create_stream_checkout_session(
        stream_id=stream_id,
        user_id=user_id,
        transaction_id=transaction.id,
        title=stream.title,
        amount=setting.price_amount,
        currency=setting.currency,
    )

    set_transaction_provider_session(
        session=session,
        transaction=transaction,
        provider_session_id=checkout_session.id,
    )

    session.commit()
    session.refresh(transaction)

    return {
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
        "transaction_id": transaction.id,
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

    event_type = event["type"]

    if event_type != "checkout.session.completed":
        return {
            "status": "ignored",
            "event_type": event_type,
        }, None

    # Convert StripeObject to normal dict.
    checkout_session = event["data"]["object"].to_dict_recursive()

    checkout_session_id = checkout_session.get("id")
    payment_intent_id = checkout_session.get("payment_intent")
    metadata = checkout_session.get("metadata") or {}

    print("[Stripe Webhook] checkout.session.completed")
    print("[Stripe Webhook] checkout_session_id=", checkout_session_id)
    print("[Stripe Webhook] payment_intent_id=", payment_intent_id)
    print("[Stripe Webhook] metadata=", metadata)

    transaction = get_transaction_by_provider_session(
        session=session,
        provider_session_id=checkout_session_id,
    )

    if not transaction:
        print("[Stripe Webhook] transaction not found for session:", checkout_session_id)

        return {
            "status": "ignored",
            "reason": "transaction_not_found",
            "checkout_session_id": checkout_session_id,
        }, None

    if transaction.status == TransactionStatus.PAID:
        print("[Stripe Webhook] transaction already paid:", transaction.id)

        return {
            "status": "already_paid",
            "transaction_id": transaction.id,
        }, None

    already_paid = has_paid_for_stream(
        session=session,
        stream_id=transaction.stream_id,
        user_id=transaction.user_id,
    )

    if already_paid:
        cancel_transaction(session, transaction)
        session.commit()

        print("[Stripe Webhook] duplicate paid checkout cancelled:", transaction.id)

        return {
            "status": "duplicate_cancelled",
            "transaction_id": transaction.id,
        }, None

    try:
        mark_transaction_paid(
            session=session,
            transaction=transaction,
            provider_payment_id=payment_intent_id,
        )

        session.commit()
        session.refresh(transaction)

        print("[Stripe Webhook] marked transaction paid:", transaction.id)

        return {
            "status": "paid",
            "transaction_id": transaction.id,
        }, None

    except IntegrityError as e:
        session.rollback()

        print("[Stripe Webhook] integrity error while marking paid:", str(e))

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