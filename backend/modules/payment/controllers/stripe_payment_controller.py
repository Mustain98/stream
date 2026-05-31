from sqlmodel import Session
from models import Stream

from modules.payment.services.payment_flow_service import (
    validate_broadcaster_stripe_account,
    validate_stream_pricing,
    handle_existing_checkout,
    calculate_transaction_fees,
    initialize_new_stripe_checkout,
    verify_and_finalize_successful_payment,
    get_and_validate_checkout_session,
    PaymentFlowError
)
from modules.payment.services.transaction_service import has_paid_for_stream, cancel_stuck_pending_transactions_for_stream_user


def create_stripe_checkout_controller(session: Session, stream: Stream, user_id: str):
    if str(stream.broadcaster_id) == str(user_id):
        raise PaymentFlowError("publisher_cannot_pay", "Publisher cannot pay for own stream")

    setting = validate_stream_pricing(session, stream.id)
    connect_account = validate_broadcaster_stripe_account(session, str(stream.broadcaster_id))

    if has_paid_for_stream(session, stream.id, user_id):
        return {"status": "already_paid", "stream_id": stream.id}

    existing_result = handle_existing_checkout(session, stream.id, user_id)
    if existing_result:
        return existing_result

    cancel_stuck_pending_transactions_for_stream_user(
        session=session, stream_id=stream.id, user_id=user_id, provider="stripe"
    )
    session.commit()

    fees = calculate_transaction_fees(setting.price_amount)

    return initialize_new_stripe_checkout(
        session=session,
        stream=stream,
        user_id=user_id,
        setting=setting,
        connect_account=connect_account,
        fees=fees,
    )


def reconcile_checkout_session_controller(session: Session, checkout_session_id: str, user_id: str):
    payment_intent_id, transaction = get_and_validate_checkout_session(
        session, checkout_session_id, user_id
    )

    return verify_and_finalize_successful_payment(
        session=session,
        transaction=transaction,
        checkout_session_id=checkout_session_id,
        payment_intent_id=payment_intent_id,
        event_id=None,
        event_type="manual_reconcile",
    )
