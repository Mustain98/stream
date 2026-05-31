from fastapi import HTTPException
from sqlmodel import Session

from models import EventType, Stream
from modules.stream.services.stream_control import (
    get_stream_block,
    get_blocked_users_for_stream,
    create_stream_block,
    delete_stream_block,
    get_user,
)
from modules.stream.services.session_viewer import (
    get_active_viewer,
    make_viewer_inactive,
)
from modules.stream.services.stream_event_service import create_stream_event
from modules.stream.services.stream_server_client import (
    kick_user_from_sfu,
    unblock_user_from_sfu,
)


def list_blocked_users_controller(
    session: Session,
    stream: Stream,
):
    return {
        "stream_id": stream.id,
        "blocked_users": get_blocked_users_for_stream(session, stream.id),
    }


async def block_viewer_controller(
    session: Session,
    stream: Stream,
    user_id: str,
    reason: str | None = "blocked",
):
    if str(stream.broadcaster_id) == str(user_id):
        raise HTTPException(status_code=400, detail="You cannot block yourself")

    blocked_user = get_user(session, user_id)

    if not blocked_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_block = get_stream_block(
        session=session,
        stream_id=stream.id,
        user_id=user_id,
    )

    if existing_block:
        blocked = existing_block
    else:
        active_viewer = get_active_viewer(
            session=session,
            user_id=user_id,
            stream_id=stream.id,
        )

        if active_viewer:
            make_viewer_inactive(session, active_viewer)

        create_stream_event(
            session=session,
            stream_id=stream.id,
            user_id=user_id,
            event_type=EventType.BLOCK,
        )

        blocked = create_stream_block(
            session=session,
            stream_id=stream.id,
            user_id=user_id,
            reason=reason,
        )

        session.commit()
        session.refresh(blocked)

    sfu_result = await kick_user_from_sfu(
        stream_id=stream.id,
        user_id=user_id,
        reason=reason or "blocked",
    )

    return {
        "status": "blocked",
        "stream_id": stream.id,
        "user_id": user_id,
        "reason": reason,
        "sfu": sfu_result,
    }


async def unblock_viewer_controller(
    session: Session,
    stream: Stream,
    user_id: str,
):
    unblocked_user = get_user(session, user_id)

    if not unblocked_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_block = get_stream_block(
        session=session,
        stream_id=stream.id,
        user_id=user_id,
    )

    if not existing_block:
        result = "not_blocked"
    else:
        delete_stream_block(session, existing_block)

        create_stream_event(
            session=session,
            stream_id=stream.id,
            user_id=user_id,
            event_type=EventType.UNBLOCK,
        )

        session.commit()

        result = "unblocked"

    sfu_result = await unblock_user_from_sfu(
        stream_id=stream.id,
        user_id=user_id,
    )

    return {
        "status": result,
        "stream_id": stream.id,
        "user_id": user_id,
        "sfu": sfu_result,
    }