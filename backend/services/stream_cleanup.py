import asyncio
from datetime import datetime

from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from db.session import engine
from models import Stream, StreamStatus

CLEANUP_INTERVAL_SECONDS = 30


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

            stream.status = StreamStatus.ENDED
            stream.ended_at = now
            stream.live_expires_at = None

            session.add(stream)

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