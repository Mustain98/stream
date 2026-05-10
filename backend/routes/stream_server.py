import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from db.session import get_session
from controllers.stream_server_controller import publisher_heartbeat_controller

load_dotenv()

router = APIRouter(prefix="/internal/sfu", tags=["internal-sfu"])

SFU_INTERNAL_SECRET = os.getenv("SFU_INTERNAL_SECRET")
LIVE_TTL_SECONDS = int(os.getenv("LIVE_TTL_SECONDS", "180"))


def verify_sfu_internal_secret(x_sfu_secret: str | None):
    if not SFU_INTERNAL_SECRET:
        raise HTTPException(
            status_code=500,
            detail="SFU_INTERNAL_SECRET is not configured",
        )

    if x_sfu_secret != SFU_INTERNAL_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid SFU internal secret",
        )


@router.post("/publisher-heartbeat/{stream_id}")
def publisher_heartbeat(
    stream_id: str,
    x_sfu_secret: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    verify_sfu_internal_secret(x_sfu_secret)

    response, error = publisher_heartbeat_controller(
        session=session,
        stream_id=stream_id,
        ttl_seconds=LIVE_TTL_SECONDS,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    return response