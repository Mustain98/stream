import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from db.session import get_session
from models import Stream,StreamStatus

load_dotenv()

router = APIRouter(prefix="/internal/sfu", tags=["internal-sfu"])

SFU_INTERNAL_SECRET = os.getenv("SFU_INTERNAL_SECRET")
LIVE_TTL_SECONDS = int(os.getenv("LIVE_TTL_SECONDS", "180"))


def utc_now():
    return datetime.utcnow()


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

    stream = session.get(Stream, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    print(
        "[SFU HEARTBEAT] received:",
        "stream_id=", stream.id,
        "status=", stream.status,
        "old_live_expires_at=", stream.live_expires_at,
    )

    if stream.status != StreamStatus.LIVE:
        print("[SFU HEARTBEAT] ignored because stream is not LIVE")
        return {
            "status": "ignored",
            "reason": "stream_not_live",
        }

    now = utc_now()
    new_expiry = now + timedelta(seconds=LIVE_TTL_SECONDS)

    stream.live_expires_at = new_expiry

    session.add(stream)
    session.commit()
    session.refresh(stream)

    print(
        "[SFU HEARTBEAT] extended:",
        "stream_id=", stream.id,
        "new_live_expires_at=", stream.live_expires_at,
        "now=", now,
        "ttl=", LIVE_TTL_SECONDS,
    )

    return {
        "status": "ok",
        "stream_id": stream.id,
        "live_expires_at": stream.live_expires_at,
    }