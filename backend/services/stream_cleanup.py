import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from db.session import engine
from models import Stream, StreamStatus, EventType
from services.stream_service import mark_stream_ended
from services.session_viewer import make_active_viewers_inactive
from services.stream_event_service import create_stream_event

load_dotenv()

CLEANUP_INTERVAL_SECONDS = int(
    os.getenv("STREAM_CLEANUP_INTERVAL_SECONDS", "30")
)


def utc_now():
    return datetime.utcnow()


def expire_stale_live_streams() -> int:
    with Session(engine) as session:
        now = utc_now()

        stale_streams = session.exec(
            select(Stream).where(
                Stream.status == StreamStatus.LIVE,
                Stream.live_expires_at != None,
                Stream.live_expires_at < now,
            )
        ).all()

        for stream in stale_streams:
            print(
                "[TTL] Expiring stale stream:",
                stream.id,
                "live_expires_at=",
                stream.live_expires_at,
                "now=",
                now,
            )

            viewer_count = make_active_viewers_inactive(
                session=session,
                stream_id=stream.id,
            )

            print(f"[TTL] Marked {viewer_count} viewer session(s) as left")

            mark_stream_ended(session, stream)

            create_stream_event(
                session=session,
                stream_id=stream.id,
                user_id=stream.broadcaster_id,
                event_type=EventType.END,
                message="Stream ended automatically because publisher heartbeat expired.",
            )

        if stale_streams:
            session.commit()
            print(f"[TTL] Expired {len(stale_streams)} stream(s)")

        return len(stale_streams)


async def stream_cleanup_loop():
    print("[TTL] Stream cleanup loop started")

    while True:
        try:
            print("[TTL] Checking stale streams...")

            expired_count = expire_stale_live_streams()

            print(f"[TTL] Cleanup check complete. Expired: {expired_count}")

        except OperationalError as e:
            print("[TTL] Database connection lost. Disposing engine pool:", str(e))
            engine.dispose()

        except Exception as e:
            print("[TTL] Cleanup error:", str(e))

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)