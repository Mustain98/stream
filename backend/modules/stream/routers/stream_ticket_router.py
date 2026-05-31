from fastapi import APIRouter, Depends
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from core.dependencies import get_valid_stream
from models import Stream, User
from modules.stream.controllers.stream_ticket_controller import create_sfu_ticket_controller

router = APIRouter(prefix="/sfu", tags=["sfu"])


@router.post("/ticket/{stream_id}")
def get_sfu_ticket(
    stream: Stream = Depends(get_valid_stream),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return create_sfu_ticket_controller(
        session=session,
        stream=stream,
        user=user,
    )