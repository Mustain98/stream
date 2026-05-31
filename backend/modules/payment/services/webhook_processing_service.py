import os
import stripe
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from modules.payment.services.transaction_service import (
    has_paid_for_stream,
    get_transaction,
    get_transaction_by_provider_session,
    has_processed_stripe_event,
    record_stripe_event_processed,
)
from modules.payment.services.stream_payment_settlement_service import stripe_object_to_dict
from modules.payment.services.payment_flow_service import verify_and_finalize_successful_payment, PaymentFlowError

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


def process_stripe_webhook(
    payload: bytes,
    signature: str,
    session: Session,
):
    if not STRIPE_WEBHOOK_SECRET:
        raise PaymentFlowError("missing_webhook_secret", "STRIPE_WEBHOOK_SECRET is not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        raise PaymentFlowError("invalid_payload", "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise PaymentFlowError("invalid_signature", "Invalid signature")

    event_id = event["id"]
    event_type = event["type"]

    event_object = stripe_object_to_dict(event["data"]["object"])
    object_id = event_object.get("id")

    if has_processed_stripe_event(session, event_id):
        return {
            "status": "duplicate_ignored",
            "event_id": event_id,
        }

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
        }

    checkout_session = event_object

    checkout_session_id = checkout_session.get("id")
    payment_intent_id = checkout_session.get("payment_intent")
    payment_status = checkout_session.get("payment_status")
    metadata = checkout_session.get("metadata") or {}

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
        }

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

        return {
            "status": "ignored",
            "reason": "transaction_not_found",
            "checkout_session_id": checkout_session_id,
        }

    if str(metadata.get("transaction_id")) != str(transaction.id) or \
       str(metadata.get("stream_id")) != str(transaction.stream_id) or \
       str(metadata.get("user_id")) != str(transaction.user_id) or \
       str(metadata.get("broadcaster_id")) != str(transaction.broadcaster_id):
        raise PaymentFlowError("metadata_mismatch", "Stripe metadata mismatch")

    try:
        return verify_and_finalize_successful_payment(
            session=session,
            transaction=transaction,
            checkout_session_id=checkout_session_id,
            payment_intent_id=payment_intent_id,
            event_id=event_id,
            event_type=event_type,
        )

    except IntegrityError as e:
        session.rollback()

        already_paid_after_rollback = has_paid_for_stream(
            session=session,
            stream_id=transaction.stream_id,
            user_id=transaction.user_id,
        )

        if already_paid_after_rollback:
            return {
                "status": "already_paid",
                "transaction_id": transaction.id,
            }

        raise
