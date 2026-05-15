from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
from models import StreamStatus, EventType
from services.stream_service import (
    get_stream,
    list_live_stream_records,
    list_owned_stream_records,
    create_stream_record,
    mark_stream_live,
    mark_stream_ended,
)
from services.earnings_service import build_stream_earnings_summary
from services.session_viewer import (
    create_viewer_session,
    get_active_viewer,
    get_unique_viewer_count,
    make_active_viewers_inactive,
    make_viewer_inactive,
)
from services.stream_event_service import create_stream_event


def stream_summary(session: Session, stream):
    return {
        "id": stream.id,
        "title": stream.title,
        "description": stream.description,
        "status": stream.status.value,
        "broadcaster_id": stream.broadcaster_id,
        "started_at": stream.started_at,
        "viewer_count": get_unique_viewer_count(session, stream.id),
    }


def list_live_streams_controller(session: Session):
    streams = list_live_stream_records(session)

    return [stream_summary(session, stream) for stream in streams]


def list_owned_streams_controller(session: Session, user_id: str):
    streams = list_owned_stream_records(session, user_id)

    return [stream_summary(session, stream) for stream in streams]


def get_stream_earnings_controller(
    session: Session,
    stream_id: str,
    user_id: str,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    if str(stream.broadcaster_id) != str(user_id):
        return None, "not_allowed"

    return build_stream_earnings_summary(
        session=session,
        stream=stream,
    ), None


def create_stream_controller(session: Session, user_id: str, payload):
    stream = create_stream_record(
        session=session,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
    )

    session.commit()
    session.refresh(stream)

    return stream


def start_stream_controller(session: Session, stream_id: str, user_id: str):
    stream = get_stream(session, stream_id)

    if not stream or str(stream.broadcaster_id) != str(user_id):
        return None

    if stream.status == StreamStatus.ENDED:
        return None

    mark_stream_live(session, stream)

    create_stream_event(
        session=session,
        stream_id=stream.id,
        user_id=user_id,
        event_type=EventType.START,
    )

    session.commit()
    session.refresh(stream)

    return stream


def end_stream_controller(session: Session, stream_id: str, user_id: str):
    stream = get_stream(session, stream_id)

    if not stream or str(stream.broadcaster_id) != str(user_id):
        return None

    mark_stream_ended(session, stream)

    make_active_viewers_inactive(session, stream.id)

    create_stream_event(
        session=session,
        stream_id=stream.id,
        user_id=user_id,
        event_type=EventType.END,
    )

    session.commit()
    session.refresh(stream)

    return stream


def join_stream_controller(session: Session, stream_id: str, user_id: str):
    stream = get_stream(session, stream_id)

    if not stream or stream.status != StreamStatus.LIVE:
        return None

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
    
def leave_stream_controller(session: Session, stream_id: str, user_id: str):
    stream = get_stream(session, stream_id)

    if not stream or stream.status != StreamStatus.LIVE:
        return None

    viewer = get_active_viewer(
        session=session,
        user_id=user_id,
        stream_id=stream.id,
    )

    if not viewer:
        return None

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
