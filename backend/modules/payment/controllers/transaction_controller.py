from fastapi import HTTPException
from sqlmodel import Session

from models import StreamAccessType, Stream
from modules.payment.services.earnings_relay_service import relay_stream_earnings_update
from modules.payment.services.transaction_service import (
    get_or_create_access_setting,
    update_access_setting,
    has_paid_for_stream,
    create_pending_transaction,
    mark_transaction_paid,
)


def get_stream_access_controller(
    session: Session,
    stream: Stream,
    user_id: str | None,
):
    setting = get_or_create_access_setting(session, stream.id)

    has_paid = False

    if user_id:
        has_paid = has_paid_for_stream(session, stream.id, user_id)

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
        "stream_id": stream.id,
        "access_type": setting.access_type.value,
        "price_amount": setting.price_amount,
        "currency": setting.currency,
        "free_preview_seconds": setting.free_preview_seconds,
        "has_paid": has_paid,
        "can_watch": can_watch,
        "access_mode": access_mode,
    }


def update_stream_access_settings_controller(
    session: Session,
    stream: Stream,
    payload,
):
    setting = get_or_create_access_setting(session, stream.id)

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

    return setting
