from fastapi import HTTPException
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from models import StreamStatus, EventType, Stream
from modules.viewer.services.session_service import (
    create_viewer_session,
    get_active_viewer,
    make_viewer_inactive,
)
from modules.stream.services.stream_event_service import create_stream_event


def join_stream_controller(session: Session, stream: Stream, user_id: str):
    if str(stream.broadcaster_id) == str(user_id):
        raise HTTPException(status_code=403, detail="Broadcaster cannot join own stream as viewer")

    if stream.status != StreamStatus.LIVE:
        raise HTTPException(status_code=400, detail="Stream not live")

    existing = get_active_viewer(
        session=session,
        user_id=user_id,
        stream_id=stream.id,
    )

    if existing:
        return existing

    viewer = create_viewer_session(
        user_id=user_id,
        stream_id=stream.id,
    )

    session.add(viewer)

    create_stream_event(
        session=session,
        stream_id=stream.id,
        user_id=user_id,
        event_type=EventType.JOIN,
    )

    try:
        session.commit()
        session.refresh(viewer)
        return viewer

    except IntegrityError:
        session.rollback()

        existing = get_active_viewer(
            session=session,
            user_id=user_id,
            stream_id=stream.id,
        )

        if existing:
            return existing

        raise


def leave_stream_controller(session: Session, stream: Stream, user_id: str):
    if stream.status != StreamStatus.LIVE:
        raise HTTPException(status_code=400, detail="Stream not live")

    viewer = get_active_viewer(
        session=session,
        user_id=user_id,
        stream_id=stream.id,
    )

    if not viewer:
        raise HTTPException(status_code=400, detail="Not in stream")

    make_viewer_inactive(session, viewer)

    create_stream_event(
        session=session,
        stream_id=stream.id,
        user_id=user_id,
        event_type=EventType.LEAVE,
    )

    session.commit()
    session.refresh(viewer)

    return viewer
