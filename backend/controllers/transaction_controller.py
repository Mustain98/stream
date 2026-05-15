from sqlmodel import Session

from models import StreamAccessType
from services.stream_service import get_stream
from services.earnings_relay_service import relay_stream_earnings_update
from services.stripe_connect_account_service import (
    get_stripe_connect_account_by_user_id,
)
from services.transaction_service import (
    get_or_create_access_setting,
    update_access_setting,
    has_paid_for_stream,
    create_pending_transaction,
    mark_transaction_paid,
)


def get_stream_access_controller(
    session: Session,
    stream_id: str,
    user_id: str | None,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    setting = get_or_create_access_setting(session, stream_id)

    has_paid = False

    if user_id:
        has_paid = has_paid_for_stream(session, stream_id, user_id)

    is_free = setting.access_type == StreamAccessType.FREE

    if is_free:
        access_mode = "free"
        can_watch = True
    elif has_paid:
        access_mode = "paid"
        can_watch = True
    elif setting.free_preview_seconds > 0:
        access_mode = "preview"
        can_watch = True
    else:
        access_mode = "payment_required"
        can_watch = False

    session.commit()

    return {
        "stream_id": stream_id,
        "access_type": setting.access_type.value,
        "price_amount": setting.price_amount,
        "currency": setting.currency,
        "free_preview_seconds": setting.free_preview_seconds,
        "has_paid": has_paid,
        "can_watch": can_watch,
        "access_mode": access_mode,
    }, None


def update_stream_access_settings_controller(
    session: Session,
    stream_id: str,
    broadcaster_id: str,
    payload,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    if str(stream.broadcaster_id) != str(broadcaster_id):
        return None, "not_allowed"

    if payload.access_type.lower() == "paid":
        if payload.price_amount <= 0:
            return None, "invalid_price"

        connect_account = get_stripe_connect_account_by_user_id(
            session=session,
            user_id=str(broadcaster_id),
        )

        if not connect_account:
            return None, "stripe_not_connected"

        if not connect_account.onboarding_completed:
            return None, "stripe_onboarding_incomplete"

    if payload.free_preview_seconds < 0:
        return None, "invalid_preview"

    setting = get_or_create_access_setting(session, stream_id)

    update_access_setting(
        session=session,
        setting=setting,
        access_type=payload.access_type,
        price_amount=payload.price_amount,
        currency=payload.currency,
        free_preview_seconds=payload.free_preview_seconds,
    )

    session.commit()
    session.refresh(setting)

    return setting, None


def create_manual_paid_transaction_controller(
    session: Session,
    stream_id: str,
    current_user_id: str,
    payload,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    setting = get_or_create_access_setting(session, stream_id)

    if setting.access_type == StreamAccessType.FREE:
        return None, "stream_is_free"

    target_user_id = payload.user_id or current_user_id

    existing_paid = has_paid_for_stream(
        session=session,
        stream_id=stream_id,
        user_id=target_user_id,
    )

    if existing_paid:
        return {
            "status": "already_paid",
            "stream_id": stream_id,
            "user_id": target_user_id,
        }, None

    transaction = create_pending_transaction(
        session=session,
        stream_id=stream_id,
        user_id=target_user_id,
        broadcaster_id=str(stream.broadcaster_id),
        amount=setting.price_amount,
        currency=setting.currency,
        provider="manual",
        platform_fee_amount=0,
        broadcaster_amount=setting.price_amount,
    )

    mark_transaction_paid(session, transaction)

    session.commit()
    session.refresh(transaction)
    relay_stream_earnings_update(
        session=session,
        stream_id=stream_id,
    )

    return {
        "id": transaction.id,
        "stream_id": transaction.stream_id,
        "user_id": transaction.user_id,
        "broadcaster_id": transaction.broadcaster_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "platform_fee_amount": transaction.platform_fee_amount,
        "broadcaster_amount": transaction.broadcaster_amount,
        "status": transaction.status.value,
        "provider": transaction.provider,
    }, None
