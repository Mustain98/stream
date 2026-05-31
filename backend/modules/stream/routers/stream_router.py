from fastapi import APIRouter, Depends
from sqlmodel import Session

from db.session import get_session
from core.security import get_current_user
from core.dependencies import get_valid_stream, require_stream_broadcaster
from models import Stream, User
from modules.stream.controllers.stream_controller import (
    create_stream_controller,
    get_stream_earnings_controller,
    start_stream_controller,
    end_stream_controller,
    join_stream_controller,
    leave_stream_controller,
    list_live_streams_controller,
    list_owned_streams_controller,
    list_upcoming_streams_controller,
)

from schemas import StreamCreate, LiveStreamSummary

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/live", response_model=list[LiveStreamSummary])
def live_streams(session: Session = Depends(get_session)):
    return list_live_streams_controller(session)


@router.get("/upcoming", response_model=list[LiveStreamSummary])
def upcoming_streams(session: Session = Depends(get_session)):
    return list_upcoming_streams_controller(session)


@router.get("/owned", response_model=list[LiveStreamSummary])
def owned_streams(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return list_owned_streams_controller(session, user.id)


@router.get("/{stream_id}/earnings")
def stream_earnings(
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
):
    return get_stream_earnings_controller(
        session=session,
        stream=stream,
    )


@router.get("/{stream_id}")
def get(
    stream: Stream = Depends(get_valid_stream),
):
    return {
        "stream": stream,
    }


@router.post("/create")
def create(
    payload: StreamCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return create_stream_controller(session, str(user.id), payload)


@router.post("/start/{stream_id}")
def start(
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return start_stream_controller(session, stream, str(user.id))


@router.post("/end/{stream_id}")
def end(
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return end_stream_controller(session, stream, str(user.id))


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
