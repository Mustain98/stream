from sqlmodel import Session

from models import Stream
from modules.earnings.services.earnings_service import (
    build_stream_earnings_summary,
    build_broadcaster_earnings_history,
    build_viewer_spend_history,
    list_transactions_for_broadcaster,
    list_transactions_for_viewer,
)


def get_stream_earnings_controller(
    session: Session,
    stream: Stream,
):
    return build_stream_earnings_summary(
        session=session,
        stream=stream,
    )


def get_broadcaster_earnings_history_controller(
    session: Session,
    user_id: str,
    year: int | None,
    month: int | None,
):
    transactions = list_transactions_for_broadcaster(session, user_id)
    return build_broadcaster_earnings_history(transactions, year=year, month=month)


def get_viewer_spend_history_controller(
    session: Session,
    user_id: str,
    year: int | None,
    month: int | None,
):
    transactions = list_transactions_for_viewer(session, user_id)
    return build_viewer_spend_history(transactions, year=year, month=month)
