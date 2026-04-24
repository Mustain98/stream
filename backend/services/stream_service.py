from sqlmodel import Session, select
from datetime import datetime
from models import Stream, StreamStatus, StreamEvent, EventType, ViewerSession
from schemas import StreamCreate


def get_stream(session: Session, stream_id: str):
    return session.get(Stream, stream_id)

def get_viewer_count(session: Session, stream_id: str):
    viewers = session.exec(
        select(ViewerSession).where(
            ViewerSession.stream_id == stream_id,
            ViewerSession.is_active == True
        )
    ).all()

    return len(viewers)


def list_live_streams(session: Session):
    streams = session.exec(
        select(Stream).where(Stream.status == StreamStatus.LIVE).order_by(Stream.started_at.desc())
    ).all()

    return [
        {
            "id": stream.id,
            "title": stream.title,
            "description": stream.description,
            "status": stream.status.value,
            "broadcaster_id": stream.broadcaster_id,
            "started_at": stream.started_at,
            "viewer_count": get_viewer_count(session, stream.id),
        }
        for stream in streams
    ]


def list_owned_streams(session: Session, user_id: str):
    streams = session.exec(
        select(Stream).where(Stream.broadcaster_id == user_id).order_by(Stream.created_at.desc())
    ).all()

    return [
        {
            "id": stream.id,
            "title": stream.title,
            "description": stream.description,
            "status": stream.status.value,
            "broadcaster_id": stream.broadcaster_id,
            "started_at": stream.started_at,
            "viewer_count": get_viewer_count(session, stream.id),
        }
        for stream in streams
    ]


def create_stream(session: Session, user_id: str, payload):
    stream = Stream(
        title=payload.title,
        description=payload.description,
        broadcaster_id=user_id
    )

    session.add(stream)
    session.commit()
    session.refresh(stream)

    return stream

def start_stream(session: Session, stream_id: str, user_id: str):
    stream = session.get(Stream, stream_id)

    if not stream or stream.broadcaster_id != user_id:
        return None

    stream.status = StreamStatus.LIVE
    stream.started_at = datetime.utcnow()

    session.add(stream)

    event = StreamEvent(
        stream_id=stream.id,
        user_id=user_id,
        event_type=EventType.START
    )

    session.add(event)

    session.commit()
    session.refresh(stream)

    return stream

def end_stream(session: Session, stream_id: str, user_id: str):
    stream = session.get(Stream, stream_id)

    if not stream or stream.broadcaster_id != user_id:
        return None

    stream.status = StreamStatus.ENDED
    stream.ended_at = datetime.utcnow()

    session.add(stream)

    event = StreamEvent(
        stream_id=stream.id,
        user_id=user_id,
        event_type=EventType.END
    )

    session.add(event)

    session.commit()
    session.refresh(stream)

    return stream


def join_stream(session: Session, stream_id: str, user_id: str):
    stream = session.get(Stream, stream_id)

    if not stream or stream.status != StreamStatus.LIVE:
        return None

    existing = session.exec(
        select(ViewerSession).where(
            ViewerSession.stream_id == stream_id,
            ViewerSession.user_id == user_id,
            ViewerSession.is_active == True
        )
    ).first()

    if existing:
        return existing

    viewer = ViewerSession(
        stream_id=stream_id,
        user_id=user_id,
        is_active=True
    )

    session.add(viewer)

    event = StreamEvent(
        stream_id=stream_id,
        user_id=user_id,
        event_type=EventType.JOIN
    )

    session.add(event)

    session.commit()
    session.refresh(viewer)

    return viewer

def leave_stream(session: Session, stream_id: str, user_id: str):

    stream = session.get(Stream, stream_id)


    if not stream or stream.status != StreamStatus.LIVE:
        return None

    viewer = session.exec(
        select(ViewerSession).where(
            ViewerSession.stream_id == stream_id,
            ViewerSession.user_id == user_id,
            ViewerSession.is_active == True
        )
    ).first()

    if not viewer:
        return None

    viewer.is_active = False
    viewer.left_at = datetime.utcnow()

    session.add(viewer)

    event = StreamEvent(
        stream_id=stream_id,
        user_id=user_id,
        event_type=EventType.LEAVE
    )

    session.add(event)

    session.commit()
    session.refresh(viewer)

    return viewer
    
