from sqlmodel import Session

from models import EventType
from services.stream_service import get_stream
from services.stream_control import (
    get_stream_block,
    get_blocked_users_for_stream,
    create_stream_block,
    delete_stream_block,
    get_user,
)
from services.session_viewer import (
    get_active_viewer,
    make_viewer_inactive,
)
from services.stream_event_service import create_stream_event
from services.stream_server_client import (
    kick_user_from_sfu,
    unblock_user_from_sfu,
)


def list_blocked_users_controller(
    session: Session,
    stream_id: str,
    current_user_id: str,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "not_found"

    if str(stream.broadcaster_id) != str(current_user_id):
        return None, "not_allowed"

    return {
        "stream_id": stream_id,
        "blocked_users": get_blocked_users_for_stream(session, stream_id),
    }, None


async def block_viewer_controller(
    session: Session,
    stream_id: str,
    user_id: str,
    current_user_id: str,
    reason: str | None = "blocked",
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    if str(stream.broadcaster_id) != str(current_user_id):
        return None, "not_allowed"

    if str(current_user_id) == str(user_id):
        return None, "self_block"

    blocked_user = get_user(session, user_id)

    if not blocked_user:
        return None, "user_not_found"

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
    }, None


async def unblock_viewer_controller(
    session: Session,
    stream_id: str,
    user_id: str,
    current_user_id: str,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

    if str(stream.broadcaster_id) != str(current_user_id):
        return None, "not_allowed"

    unblocked_user = get_user(session, user_id)

    if not unblocked_user:
        return None, "user_not_found"

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
    }, None