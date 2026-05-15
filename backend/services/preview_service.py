from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from models import StreamPreviewUsage


def utc_now() -> datetime:
    return datetime.utcnow()


def get_preview_usage(
    session: Session,
    stream_id: str,
    user_id: str,
) -> Optional[StreamPreviewUsage]:
    return session.exec(
        select(StreamPreviewUsage).where(
            StreamPreviewUsage.stream_id == stream_id,
            StreamPreviewUsage.user_id == user_id,
        )
    ).first()


def get_or_create_preview_usage(
    session: Session,
    stream_id: str | UUID,
    user_id: str | UUID,
    preview_limit_seconds: int,
) -> StreamPreviewUsage:
    usage = get_preview_usage(session, stream_id, user_id)

    if usage:
        return usage

    now = utc_now()

    usage = StreamPreviewUsage(
        stream_id=stream_id,
        user_id=user_id,
        preview_limit_seconds=preview_limit_seconds,
        used_seconds=0,
        active_started_at=None,
        exhausted_at=None,
        created_at=now,
        updated_at=now,
    )

    session.add(usage)
    session.commit()
    session.refresh(usage)

    return usage


def calculate_remaining_preview_seconds(
    usage: StreamPreviewUsage,
) -> int:
    now = utc_now()

    total_used = usage.used_seconds

    if usage.active_started_at is not None:
        active_used = int((now - usage.active_started_at).total_seconds())
        total_used += max(0, active_used)

    remaining = usage.preview_limit_seconds - total_used

    return max(0, remaining)


def get_remaining_preview_seconds(
    session: Session,
    stream_id: str | UUID,
    user_id: str | UUID,
    preview_limit_seconds: int,
) -> int:
    if preview_limit_seconds <= 0:
        return 0

    usage = get_or_create_preview_usage(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        preview_limit_seconds=preview_limit_seconds,
    )

    remaining = calculate_remaining_preview_seconds(usage)

    if remaining <= 0 and usage.exhausted_at is None:
        now = utc_now()
        usage.exhausted_at = now
        usage.updated_at = now
        session.add(usage)
        session.commit()

    return remaining


def start_preview_session(
    session: Session,
    stream_id: str | UUID,
    user_id: str | UUID,
    preview_limit_seconds: int,
) -> int:
    usage = get_or_create_preview_usage(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        preview_limit_seconds=preview_limit_seconds,
    )

    remaining = calculate_remaining_preview_seconds(usage)

    if remaining <= 0:
        now = utc_now()

        if usage.exhausted_at is None:
            usage.exhausted_at = now
            usage.updated_at = now
            session.add(usage)
            session.commit()

        return 0

    if usage.active_started_at is None:
        now = utc_now()
        usage.active_started_at = now
        usage.updated_at = now
        session.add(usage)
        session.commit()

    return remaining


def end_preview_session(
    session: Session,
    stream_id: str | UUID,
    user_id: str | UUID,
) -> int:
    usage = get_preview_usage(session, stream_id, user_id)

    if not usage:
        return 0

    if usage.active_started_at is None:
        return calculate_remaining_preview_seconds(usage)

    now = utc_now()

    session_used = int((now - usage.active_started_at).total_seconds())
    session_used = max(0, session_used)

    usage.used_seconds += session_used
    usage.active_started_at = None
    usage.updated_at = now

    if usage.used_seconds >= usage.preview_limit_seconds:
        usage.used_seconds = usage.preview_limit_seconds
        usage.exhausted_at = now

    session.add(usage)
    session.commit()
    session.refresh(usage)

    return calculate_remaining_preview_seconds(usage)