from fastapi import APIRouter, Depends
from sqlmodel import Session

from db.session import get_session
from core.dependencies import require_stream_broadcaster
from models import Stream
from schemas.stream_control import BlockUserRequest
from modules.stream.controllers.stream_control_controller import (
    list_blocked_users_controller,
    block_viewer_controller,
    unblock_viewer_controller,
)

router = APIRouter(prefix="/stream", tags=["stream-control"])


@router.get("/{stream_id}/blocked-users")
def list_blocked_users(
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
):
    return list_blocked_users_controller(
        session=session,
        stream=stream,
    )


@router.post("/{stream_id}/block/{user_id}")
async def block_viewer(
    user_id: str,
    payload: BlockUserRequest,
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
):
    return await block_viewer_controller(
        session=session,
        stream=stream,
        user_id=user_id,
        reason=payload.reason,
    )


@router.delete("/{stream_id}/block/{user_id}")
async def unblock_viewer(
    user_id: str,
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
):
    return await unblock_viewer_controller(
        session=session,
        stream=stream,
        user_id=user_id,
    )