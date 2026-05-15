import os

from sqlmodel import Session

from core.stream_ticket import create_sfu_ticket
from models import StreamStatus, StreamAccessType
from services.stream_service import get_stream
from services.stream_control import is_user_blocked
from services.transaction_service import (
    get_or_create_access_setting,
    has_paid_for_stream,
)
from services.preview_service import get_remaining_preview_seconds


SFU_WS_URL = os.getenv("SFU_WS_URL", "ws://localhost:7001/ws")


def get_stream_access_response(
    session: Session,
    stream_id: str,
    user,
    stream,
):
    if not stream:
        return None

    setting = get_or_create_access_setting(session, stream_id)

    is_owner = str(user.id) == str(stream.broadcaster_id)

    if is_owner:
        return {
            "access_mode": "paid",
            "can_watch": True,
            "has_paid": True,
            "price_amount": setting.price_amount,
            "currency": setting.currency,
            "free_preview_seconds": 0,
        }

    if setting.access_type == StreamAccessType.FREE:
        return {
            "access_mode": "free",
            "can_watch": True,
            "has_paid": False,
            "price_amount": setting.price_amount,
            "currency": setting.currency,
            "free_preview_seconds": 0,
        }

    has_paid = has_paid_for_stream(
        session=session,
        stream_id=stream_id,
        user_id=str(user.id),
    )

    if has_paid:
        return {
            "access_mode": "paid",
            "can_watch": True,
            "has_paid": True,
            "price_amount": setting.price_amount,
            "currency": setting.currency,
            "free_preview_seconds": 0,
        }

    remaining_preview = get_remaining_preview_seconds(
        session=session,
        stream_id=stream_id,
        user_id=str(user.id),
        preview_limit_seconds=setting.free_preview_seconds,
    )

    if remaining_preview > 0:
        return {
            "access_mode": "preview",
            "can_watch": True,
            "has_paid": False,
            "price_amount": setting.price_amount,
            "currency": setting.currency,
            "free_preview_seconds": remaining_preview,
        }

    return {
        "access_mode": "payment_required",
        "can_watch": False,
        "has_paid": False,
        "price_amount": setting.price_amount,
        "currency": setting.currency,
        "free_preview_seconds": 0,
    }


def create_sfu_ticket_controller(
    session: Session,
    stream_id: str,
    user,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    role = "publisher" if str(user.id) == str(stream.broadcaster_id) else "subscriber"

    if role == "subscriber" and is_user_blocked(session, stream_id, str(user.id)):
        return None, "blocked"

    if stream.status != StreamStatus.LIVE:
        if role == "publisher":
            return None, "publisher_stream_not_live"

        return None, "stream_not_live"

    access_mode = "free"
    preview_seconds = 0

    if role == "publisher":
        access_mode = "paid"
        preview_seconds = 0

    else:
        setting = get_or_create_access_setting(session, stream_id)

        if setting.access_type == StreamAccessType.FREE:
            access_mode = "free"
            preview_seconds = 0

        else:
            has_paid = has_paid_for_stream(
                session=session,
                stream_id=stream_id,
                user_id=str(user.id),
            )

            if has_paid:
                access_mode = "paid"
                preview_seconds = 0

            elif setting.free_preview_seconds > 0:
                preview_seconds = get_remaining_preview_seconds(
                    session=session,
                    stream_id=stream_id,
                    user_id=str(user.id),
                    preview_limit_seconds=setting.free_preview_seconds,
                )

                print("preview_seconds:", preview_seconds)

                if preview_seconds <= 0:
                    return None, "payment_required"

                access_mode = "preview"

            else:
                return None, "payment_required"

    username = getattr(user, "username", None)

    token = create_sfu_ticket(
        user_id=str(user.id),
        username=username,
        stream_id=str(stream_id),
        role=role,
        access_mode=access_mode,
        preview_seconds=preview_seconds,
    )

    return {
        "sfuUrl": SFU_WS_URL,
        "token": token,
        "streamId": str(stream_id),
        "roomId": str(stream_id),
        "role": role,
        "accessMode": access_mode,
        "previewSeconds": preview_seconds,
    }, None