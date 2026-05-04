# backend/routes/websocket_ticket.py

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.security import get_current_user
from core.ws_ticket import create_sfu_ticket
from db.session import get_session
from models import Stream

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

    role = "publisher" if user.id == stream.broadcaster_id else "subscriber"

    if role == "subscriber" and stream.status != "live":
        raise HTTPException(status_code=400, detail="Stream is not live")

    token = create_sfu_ticket(
        user_id=user.id,
        stream_id=stream_id,
        role=role,
    )

    return {
        "sfuUrl": SFU_WS_URL,
        "token": token,
        "streamId": stream_id,
        "roomId": stream_id,
        "role": role,
    }