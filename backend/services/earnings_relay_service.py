from services.earnings_service import build_stream_earnings_summary
from services.stream_server_client import notify_earnings_update_in_sfu
from services.stream_service import get_stream


def relay_stream_earnings_update(
    session,
    stream_id: str,
):
    stream = get_stream(session, stream_id)

    if not stream:
        return {
            "status": "ignored",
            "reason": "stream_not_found",
            "stream_id": stream_id,
        }

    earnings_summary = build_stream_earnings_summary(
        session=session,
        stream=stream,
    )

    relay_result = notify_earnings_update_in_sfu(
        stream_id=stream_id,
        earnings_summary=earnings_summary,
    )

    return {
        "status": "ok",
        "stream_id": stream_id,
        "earnings_summary": earnings_summary,
        "relay": relay_result,
    }

