from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
from sqlmodel import Session, select

from models import Stream, StreamStatus

load_dotenv()

LIVE_TTL_SECONDS = int(os.getenv("LIVE_TTL_SECONDS", "300"))


def utc_now():
    return datetime.utcnow()


def get_stream(session: Session, stream_id: str):
    return session.get(Stream, stream_id)


def list_live_stream_records(session: Session) -> list[Stream]:
    return session.exec(
        select(Stream)
        .where(Stream.status == StreamStatus.LIVE)
        .order_by(Stream.started_at.desc())
    ).all()


def list_owned_stream_records(session: Session, user_id: str) -> list[Stream]:
    return session.exec(
        select(Stream)
        .where(Stream.broadcaster_id == user_id)
        .order_by(Stream.created_at.desc())
    ).all()


def create_stream_record(
    session: Session,
    user_id: str,
    title: str,
    description: str | None,
) -> Stream:
    stream = Stream(
        title=title,
        description=description,
        broadcaster_id=user_id,
    )

    session.add(stream)

    return stream


def mark_stream_live(session: Session, stream: Stream) -> Stream:
    now = utc_now()

    stream.status = StreamStatus.LIVE
    stream.started_at = now
    stream.ended_at = None
    stream.live_expires_at = now + timedelta(seconds=LIVE_TTL_SECONDS)

    session.add(stream)

    return stream


def mark_stream_ended(session: Session, stream: Stream) -> Stream:
    stream.status = StreamStatus.ENDED
    stream.ended_at = utc_now()
    stream.live_expires_at = None

    session.add(stream)

    return stream


def extend_stream_live_expiry(
    session: Session,
    stream: Stream,
    ttl_seconds: int,
) -> Stream:
    now = utc_now()

    stream.live_expires_at = now + timedelta(seconds=ttl_seconds)

    session.add(stream)

    return stream