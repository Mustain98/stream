import os
from fastapi import HTTPException
from sqlmodel import Session

from core.stream_ticket import create_sfu_ticket
from models import StreamStatus, StreamAccessType, Stream, User
from modules.stream.services.stream_control import is_user_blocked
from modules.payment.services.transaction_service import (
    get_or_create_access_setting,
    has_paid_for_stream,
)
from modules.stream.services.preview_service import get_remaining_preview_seconds

SFU_WS_URL = os.getenv("SFU_WS_URL", "ws://localhost:7001/ws")


def create_sfu_ticket_controller(
    session: Session,
    stream: Stream,
    user: User,
):
    role = "publisher" if str(user.id) == str(stream.broadcaster_id) else "subscriber"

    if role == "subscriber" and is_user_blocked(session, stream.id, str(user.id)):
        raise HTTPException(status_code=403, detail="You are blocked from this stream")

    if stream.status != StreamStatus.LIVE:
        if role == "publisher":
            raise HTTPException(status_code=400, detail="Start the stream before requesting an SFU ticket")
        raise HTTPException(status_code=400, detail="Stream is not live")

    access_mode = "free"
    preview_seconds = 0

    if role == "publisher":
        access_mode = "paid"
        preview_seconds = 0
    else:
        setting = get_or_create_access_setting(session, stream.id)

        if setting.access_type == StreamAccessType.FREE:
            access_mode = "free"
            preview_seconds = 0
        else:
            has_paid = has_paid_for_stream(
                session=session,
                stream_id=stream.id,
                user_id=str(user.id),
            )

            if has_paid:
                access_mode = "paid"
                preview_seconds = 0
            elif setting.free_preview_seconds > 0:
                preview_seconds = get_remaining_preview_seconds(
                    session=session,
                    stream_id=stream.id,
                    user_id=str(user.id),
                    preview_limit_seconds=setting.free_preview_seconds,
                )

                if preview_seconds <= 0:
                    raise HTTPException(status_code=402, detail="Payment required to watch this stream")

                access_mode = "preview"
            else:
                raise HTTPException(status_code=402, detail="Payment required to watch this stream")

    username = getattr(user, "username", None)

    token = create_sfu_ticket(
        user_id=str(user.id),
        username=username,
        stream_id=str(stream.id),
        role=role,
        access_mode=access_mode,
        preview_seconds=preview_seconds,
    )

    return {
        "sfuUrl": SFU_WS_URL,
        "token": token,
        "streamId": str(stream.id),
        "roomId": str(stream.id),
        "role": role,
        "accessMode": access_mode,
        "previewSeconds": preview_seconds,
    }