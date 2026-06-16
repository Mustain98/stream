from sqlmodel import Session

from models import Stream
from modules.earnings.services.earnings_service import build_stream_earnings_summary


def get_stream_earnings_controller(
    session: Session,
    stream: Stream,
):
    return build_stream_earnings_summary(
        session=session,
        stream=stream,
    )
