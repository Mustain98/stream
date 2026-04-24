from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from core.ws_ticket import create_ws_ticket
from db.session import get_session
from models import Stream

router = APIRouter()


@router.post("/ws-ticket/{stream_id}")
def get_ws_ticket(
    stream_id: str,
    user=Depends(get_current_user),
    session=Depends(get_session),
):

    stream=session.get(Stream,stream_id)

    if not stream:
        raise HTTPException(404, "Stream not found")

    role = "broadcaster" if user.id == stream.broadcaster_id else "viewer"

    ticket = create_ws_ticket(user.id, stream_id, role)

    return {
        "ticket": ticket,
        "stream_id": stream_id,
        "role": role
    }
