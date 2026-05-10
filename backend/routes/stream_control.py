from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db.session import get_session
from core.security import get_current_user
from schemas.stream_control import BlockUserRequest
from controllers.stream_control_controller import (
    list_blocked_users_controller,
    block_viewer_controller,
    unblock_viewer_controller,
)

router = APIRouter(prefix="/stream", tags=["stream-control"])


@router.get("/{stream_id}/blocked-users")
def list_blocked_users(
    stream_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    response, error = list_blocked_users_controller(
        session=session,
        stream_id=stream_id,
        current_user_id=current_user.id,
    )

    if error == "not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    if error == "not_allowed":
        raise HTTPException(status_code=403, detail="Not allowed")

    return response


@router.post("/{stream_id}/block/{user_id}")
async def block_viewer(
    stream_id: str,
    user_id: str,
    payload: BlockUserRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    response, error = await block_viewer_controller(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        current_user_id=current_user.id,
        reason=payload.reason,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    if error == "not_allowed":
        raise HTTPException(status_code=403, detail="Not allowed")

    if error == "self_block":
        raise HTTPException(status_code=400, detail="You cannot block yourself")

    if error == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")

    return response


@router.delete("/{stream_id}/block/{user_id}")
async def unblock_viewer(
    stream_id: str,
    user_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    response, error = await unblock_viewer_controller(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        current_user_id=current_user.id,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    if error == "not_allowed":
        raise HTTPException(status_code=403, detail="Not allowed")

    if error == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")

    return response