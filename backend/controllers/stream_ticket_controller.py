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

SFU_WS_URL = os.getenv("SFU_WS_URL", "ws://localhost:7001/ws")


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

    if role == "subscriber":
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
                access_mode = "preview"
                preview_seconds = setting.free_preview_seconds

            else:
                return None, "payment_required"

    # Publisher should always get full access to their own stream.
    if role == "publisher":
        access_mode = "paid"
        preview_seconds = 0

    username = getattr(user, "username", None)

    token = create_sfu_ticket(
        user_id=str(user.id),
        username=username,
        stream_id=str(stream_id),
        role=role,
        access_mode=access_mode,
        preview_seconds=preview_seconds,
    )

    session.commit()

    return {
        "sfuUrl": SFU_WS_URL,
        "token": token,
        "streamId": str(stream_id),
        "roomId": str(stream_id),
        "role": role,
        "accessMode": access_mode,
        "previewSeconds": preview_seconds,
    }, None