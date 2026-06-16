from fastapi import APIRouter, Depends
from sqlmodel import Session

from db.session import get_session
from core.security import get_current_user
from core.dependencies import get_valid_stream
from models import Stream, User
from modules.viewer.controllers.viewer_controller import (
    join_stream_controller,
    leave_stream_controller,
)

router = APIRouter(prefix="/stream", tags=["viewer"])


@router.post("/join/{stream_id}")
def join(
    stream: Stream = Depends(get_valid_stream),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return join_stream_controller(session, stream, str(user.id))


@router.post("/leave/{stream_id}")
def leave(
    stream: Stream = Depends(get_valid_stream),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return leave_stream_controller(session, stream, str(user.id))
