from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db.session import get_session
from core.security import get_current_user
from services.stream_service import (
    create_stream,
    start_stream,
    end_stream,
    join_stream,
    leave_stream,
    get_stream,
    get_viewer_count,
    list_live_streams,
    list_owned_streams,
)

from schemas import StreamCreate, LiveStreamSummary

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/live", response_model=list[LiveStreamSummary])
def live_streams(session: Session = Depends(get_session)):
    return list_live_streams(session)


@router.get("/owned", response_model=list[LiveStreamSummary])
def owned_streams(
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    return list_owned_streams(session, user.id)

@router.get("/{stream_id}")
def get(
    stream_id: str,
    session: Session = Depends(get_session)
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
    user = Depends(get_current_user)
):
    return create_stream(session, user.id, payload)

@router.post("/start/{stream_id}")
def start(
    stream_id: str,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    stream = start_stream(session, stream_id, user.id)

    if not stream:
        raise HTTPException(status_code=403, detail="Not allowed")

    return stream

@router.post("/end/{stream_id}")
def end(
    stream_id: str,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    stream = end_stream(session, stream_id, user.id)

    if not stream:
        raise HTTPException(status_code=403, detail="Not allowed")

    return stream

@router.post("/join/{stream_id}")
def join(
    stream_id: str,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    stream = get_stream(session, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Not found")

    if stream.broadcaster_id == user.id:
        raise HTTPException(status_code=403, detail="Broadcaster cannot join own stream as viewer")

    viewer = join_stream(session, stream_id, user.id)

    if not viewer:
        raise HTTPException(status_code=400, detail="Stream not live")

    return viewer

@router.post("/leave/{stream_id}")
def leave(
    stream_id: str,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    viewer = leave_stream(session, stream_id, user.id)

    if not viewer:
        raise HTTPException(status_code=400, detail="Not in stream")

    return viewer
