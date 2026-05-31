import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from sqlmodel import Session

from db.session import get_session
from core.dependencies import get_valid_stream, verify_sfu_internal_secret
from models import Stream
from modules.stream.controllers.stream_server_controller import publisher_heartbeat_controller

load_dotenv()

router = APIRouter(prefix="/internal/sfu", tags=["internal-sfu"])

LIVE_TTL_SECONDS = int(os.getenv("LIVE_TTL_SECONDS", "180"))


@router.post("/publisher-heartbeat/{stream_id}")
def publisher_heartbeat(
    stream: Stream = Depends(get_valid_stream),
    _=Depends(verify_sfu_internal_secret),
    session: Session = Depends(get_session),
):
    return publisher_heartbeat_controller(
        session=session,
        stream=stream,
        ttl_seconds=LIVE_TTL_SECONDS,
    )