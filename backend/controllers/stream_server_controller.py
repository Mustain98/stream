from sqlmodel import Session

from models import StreamStatus
from services.stream_service import get_stream, extend_stream_live_expiry


def publisher_heartbeat_controller(
    session: Session,
    stream_id: str,
    ttl_seconds: int,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return None, "stream_not_found"

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
        }, None

    extend_stream_live_expiry(
        session=session,
        stream=stream,
        ttl_seconds=ttl_seconds,
    )

    session.commit()
    session.refresh(stream)

    print(
        "[SFU HEARTBEAT] extended:",
        "stream_id=", stream.id,
        "new_live_expires_at=", stream.live_expires_at,
        "ttl=", ttl_seconds,
    )

    return {
        "status": "ok",
        "stream_id": stream.id,
        "live_expires_at": stream.live_expires_at,
    }, None