from sqlmodel import Session, select

from models import StreamBlocked, User


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


def create_stream_block(
    session: Session,
    stream_id: str,
    user_id: str,
    reason: str | None = "blocked",
) -> StreamBlocked:
    blocked = StreamBlocked(
        stream_id=stream_id,
        user_id=user_id,
        reason=reason,
    )

    session.add(blocked)

    return blocked


def delete_stream_block(session: Session, block: StreamBlocked):
    session.delete(block)


def get_user(session: Session, user_id: str):
    return session.get(User, user_id)
