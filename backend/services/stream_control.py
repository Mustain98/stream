from datetime import datetime

from sqlmodel import Session, select

from models import (
    Stream,
    StreamBlocked,
    StreamEvent,
    EventType,
    ViewerSession,
    User,
)


def get_stream_block(
    session: Session,
    stream_id: str,
    user_id: str,
):
    return session.exec(
        select(StreamBlocked).where(
            StreamBlocked.stream_id == stream_id,
            StreamBlocked.user_id == user_id,
        )
    ).first()


def is_user_blocked(
    session: Session,
    stream_id: str,
    user_id: str,
) -> bool:
    return get_stream_block(session, stream_id, user_id) is not None

def get_blocked_users_for_stream(session: Session, stream_id: str):
    blocked_rows = session.exec(
        select(StreamBlocked).where(
            StreamBlocked.stream_id == stream_id,
        )
    ).all()

    result = []

    for blocked in blocked_rows:
        user = session.get(User, blocked.user_id)

        result.append(
            {
                "id": blocked.id,
                "stream_id": blocked.stream_id,
                "user_id": blocked.user_id,
                "username": user.username if user else "Unknown",
                "reason": blocked.reason,
                "created_at": blocked.created_at,
            }
        )

    return result


def block_stream_user(
    session: Session,
    stream: Stream,
    blocked_user_id: str,
    reason: str | None = "blocked",
):
    blocked_user = session.get(User, blocked_user_id)

    if not blocked_user:
        return None

    existing_block = get_stream_block(
        session=session,
        stream_id=stream.id,
        user_id=blocked_user_id,
    )

    if existing_block:
        return existing_block

    now = datetime.utcnow()

    active_viewer_sessions = session.exec(
        select(ViewerSession).where(
            ViewerSession.stream_id == stream.id,
            ViewerSession.user_id == blocked_user_id,
            ViewerSession.is_active == True,
        )
    ).all()

    for viewer_session in active_viewer_sessions:
        viewer_session.is_active = False
        viewer_session.left_at = now
        session.add(viewer_session)

    stream_event = StreamEvent(
        stream_id=stream.id,
        user_id=blocked_user_id,
        event_type=EventType.BLOCK,
    )
    session.add(stream_event)

    blocked = StreamBlocked(
        stream_id=stream.id,
        user_id=blocked_user_id,
        reason=reason,
    )
    session.add(blocked)

    session.commit()
    session.refresh(blocked)

    return blocked


def unblock_stream_user(
    session: Session,
    stream: Stream,
    unblocked_user_id: str,
):
    unblocked_user = session.get(User, unblocked_user_id)

    if not unblocked_user:
        return None

    existing_block = get_stream_block(
        session=session,
        stream_id=stream.id,
        user_id=unblocked_user_id,
    )

    if not existing_block:
        return "not_blocked"

    session.delete(existing_block)

    stream_event = StreamEvent(
        stream_id=stream.id,
        user_id=unblocked_user_id,
        event_type=EventType.UNBLOCK,
    )
    session.add(stream_event)

    session.commit()

    return "unblocked"