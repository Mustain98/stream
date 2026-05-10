from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db.session import get_session
from core.security import get_current_user
from services.stream_service import get_stream
from controllers.stream_controller import (
    create_stream_controller,
    start_stream_controller,
    end_stream_controller,
    join_stream_controller,
    leave_stream_controller,
    list_live_streams_controller,
    list_owned_streams_controller,
)

from schemas import StreamCreate, LiveStreamSummary

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/live", response_model=list[LiveStreamSummary])
def live_streams(session: Session = Depends(get_session)):
    return list_live_streams_controller(session)


@router.get("/owned", response_model=list[LiveStreamSummary])
def owned_streams(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return list_owned_streams_controller(session, user.id)


@router.get("/{stream_id}")
def get(
    stream_id: str,
    session: Session = Depends(get_session),
):
    stream = get_stream(session, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "stream": stream,
    }


@router.post("/create")
def create(
    payload: StreamCreate,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return create_stream_controller(session, user.id, payload)


@router.post("/start/{stream_id}")
def start(
    stream_id: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    stream = start_stream_controller(session, stream_id, user.id)

    if not stream:
        raise HTTPException(status_code=403, detail="Not allowed")

    return stream


@router.post("/end/{stream_id}")
def end(
    stream_id: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    stream = end_stream_controller(session, stream_id, user.id)

    if not stream:
        raise HTTPException(status_code=403, detail="Not allowed")

    return stream


@router.post("/join/{stream_id}")
def join(
    stream_id: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    stream = get_stream(session, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Not found")

    if str(stream.broadcaster_id) == str(user.id):
        raise HTTPException(
            status_code=403,
            detail="Broadcaster cannot join own stream as viewer",
        )

    viewer = join_stream_controller(session, stream_id, user.id)

    if not viewer:
        raise HTTPException(status_code=400, detail="Stream not live")

    return viewer


@router.post("/leave/{stream_id}")
def leave(
    stream_id: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    viewer = leave_stream_controller(session, stream_id, user.id)

    if not viewer:
        raise HTTPException(status_code=400, detail="Not in stream")

    return viewer