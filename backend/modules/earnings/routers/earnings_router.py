from fastapi import APIRouter, Depends
from sqlmodel import Session

from db.session import get_session
from core.dependencies import require_stream_broadcaster
from models import Stream
from modules.earnings.controllers.earnings_controller import get_stream_earnings_controller

router = APIRouter(prefix="/stream", tags=["earnings"])


@router.get("/{stream_id}/earnings")
def stream_earnings(
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
):
    return get_stream_earnings_controller(
        session=session,
        stream=stream,
    )
