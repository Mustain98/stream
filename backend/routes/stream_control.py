from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db.session import get_session
from core.security import get_current_user
from schemas.stream_control import BlockUserRequest, UnblockUserRequest
from services.stream_service import get_stream
from services.stream_control import (
    block_stream_user,
    unblock_stream_user,
    get_blocked_users_for_stream
)
from services.stream_server_client import kick_user_from_sfu, unblock_user_from_sfu

router = APIRouter(prefix="/stream", tags=["stream-control"])

@router.get("/{stream_id}/blocked-users")
def list_blocked_users(
    stream_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stream = get_stream(session, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if str(stream.broadcaster_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not allowed")

    return {
        "stream_id": stream_id,
        "blocked_users": get_blocked_users_for_stream(session, stream_id),
    }

@router.post("/{stream_id}/block/{user_id}")
async def block_viewer(
    stream_id: str,
    user_id: str,
    payload: BlockUserRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stream = get_stream(session, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if str(stream.broadcaster_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not allowed")

    if str(current_user.id) == str(user_id):
        raise HTTPException(status_code=400, detail="You cannot block yourself")

    blocked = block_stream_user(
        session=session,
        stream=stream,
        blocked_user_id=user_id,
        reason=payload.reason,
    )

    if not blocked:
        raise HTTPException(status_code=404, detail="User not found")

    sfu_result = await kick_user_from_sfu(
        stream_id=stream_id,
        user_id=user_id,
        reason=payload.reason or "blocked",
    )

    return {
        "status": "blocked",
        "stream_id": stream_id,
        "user_id": user_id,
        "reason": payload.reason,
        "sfu": sfu_result,
    }


@router.delete("/{stream_id}/block/{user_id}")
async def unblock_viewer(
    stream_id: str,
    user_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    stream = get_stream(session, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if str(stream.broadcaster_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not allowed")

    result = unblock_stream_user(
        session=session,
        stream=stream,
        unblocked_user_id=user_id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="User not found")

    sfu_result = await unblock_user_from_sfu(
        stream_id=stream_id,
        user_id=user_id,
    )

    return {
        "status": result,
        "stream_id": stream_id,
        "user_id": user_id,
        "sfu": sfu_result,
    }