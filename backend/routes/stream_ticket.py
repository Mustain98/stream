# backend/routes/websocket_ticket.py

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.security import get_current_user
from core.stream_ticket import create_sfu_ticket
from db.session import get_session
from models import Stream, StreamStatus
from services.stream_control import is_user_blocked

router = APIRouter(prefix="/sfu", tags=["sfu"])

SFU_WS_URL = os.getenv("SFU_WS_URL", "ws://localhost:7001/ws")


@router.post("/ticket/{stream_id}")
def get_sfu_ticket(
    stream_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    stream = session.get(Stream, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    role = "publisher" if str(user.id) == str(stream.broadcaster_id) else "subscriber"

    if role == "subscriber":
        blocked = is_user_blocked(
            session=session,
            stream_id=str(stream_id),
            user_id=str(user.id),
        )

        if blocked:
            raise HTTPException(
                status_code=403,
                detail="You are blocked from this stream",
            )

    if stream.status != StreamStatus.LIVE:
        raise HTTPException(
            status_code=400,
            detail=(
                "Start the stream before requesting an SFU ticket"
                if role == "publisher"
                else "Stream is not live"
            ),
        )

    username = getattr(user, "username", None)

    token = create_sfu_ticket(
        user_id=str(user.id),
        username=username,
        stream_id=str(stream_id),
        role=role,
    )

    return {
        "sfuUrl": SFU_WS_URL,
        "token": token,
        "streamId": str(stream_id),
        "roomId": str(stream_id),
        "role": role,
    }