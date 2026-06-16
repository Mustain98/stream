from fastapi import HTTPException
from sqlmodel import Session

from models import StreamStatus, EventType, Stream
from modules.stream.services.stream_service import (
    list_live_stream_records,
    list_owned_stream_records,
    create_stream_record,
    mark_stream_live,
    mark_stream_ended,
    list_upcoming_stream_records,
)
from modules.viewer.services.session_service import (
    get_unique_viewer_count,
    make_active_viewers_inactive,
)
from modules.stream.services.stream_event_service import create_stream_event
from modules.payment.services.settlement_service import settle_stream_payment_after_end


def stream_summary(session: Session, stream: Stream):
    from models import User
    user = session.get(User, stream.broadcaster_id)
    return {
        "id": stream.id,
        "title": stream.title,
        "description": stream.description,
        "status": stream.status.value,
        "broadcaster_id": stream.broadcaster_id,
        "broadcaster_username": user.username if user else None,
        "started_at": stream.started_at,
        "scheduled_start_time": stream.scheduled_start_time,
        "scheduled_end_time": stream.scheduled_end_time,
        "viewer_count": get_unique_viewer_count(session, stream.id),
    }


def list_live_streams_controller(session: Session):
    streams = list_live_stream_records(session)
    return [stream_summary(session, stream) for stream in streams]


def list_upcoming_streams_controller(session: Session):
    streams = list_upcoming_stream_records(session)
    return [stream_summary(session, stream) for stream in streams]


def list_owned_streams_controller(session: Session, user_id: str):
    streams = list_owned_stream_records(session, user_id)
    return [stream_summary(session, stream) for stream in streams]


def create_stream_controller(session: Session, user_id: str, payload):
    stream = create_stream_record(
        session=session,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        min_duration_seconds=payload.min_duration_seconds,
        scheduled_start_time=payload.scheduled_start_time,
        scheduled_end_time=payload.scheduled_end_time,
    )

    session.commit()
    session.refresh(stream)

    return stream


def start_stream_controller(session: Session, stream: Stream, user_id: str):
    if stream.status == StreamStatus.ENDED:
        raise HTTPException(status_code=400, detail="Stream has already ended")

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


def end_stream_controller(session: Session, stream: Stream, user_id: str):
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

    settlement_result = settle_stream_payment_after_end(
        session=session,
        stream=stream,
    )

    session.commit()
    session.refresh(stream)

    return {
        "stream": stream,
        "payment_settlement": settlement_result,
    }
