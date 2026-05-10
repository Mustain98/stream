import os

from sqlmodel import Session

from core.stream_ticket import create_sfu_ticket
from models import StreamStatus
from services.stream_service import get_stream
from services.stream_control import is_user_blocked

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
    }, None