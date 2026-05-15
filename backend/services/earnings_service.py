from datetime import datetime

from sqlmodel import Session, select

from models import (
    Stream,
    StreamAccessType,
    StreamStatus,
    StreamTransaction,
    TransactionStatus,
)
from services.session_viewer import get_unique_viewer_count
from services.transaction_service import get_stream_access_setting

CHARGE_SUCCESS_STATUSES = {
    TransactionStatus.PAID,
    TransactionStatus.REFUND_PENDING,
    TransactionStatus.REFUNDED,
    TransactionStatus.REFUND_FAILED,
}

NET_EARNING_STATUSES = {
    TransactionStatus.PAID,
    TransactionStatus.REFUND_FAILED,
}


def list_transactions_for_stream(
    session: Session,
    stream_id: str,
) -> list[StreamTransaction]:
    return session.exec(
        select(StreamTransaction)
        .where(StreamTransaction.stream_id == stream_id)
        .order_by(StreamTransaction.created_at.desc())
    ).all()


def list_transactions_for_broadcaster(
    session: Session,
    broadcaster_id: str,
) -> list[StreamTransaction]:
    return session.exec(
        select(StreamTransaction)
        .where(StreamTransaction.broadcaster_id == broadcaster_id)
        .order_by(StreamTransaction.created_at.desc())
    ).all()


def list_transactions_for_viewer(
    session: Session,
    user_id: str,
) -> list[StreamTransaction]:
    return session.exec(
        select(StreamTransaction)
        .where(StreamTransaction.user_id == user_id)
        .order_by(StreamTransaction.created_at.desc())
    ).all()


def get_recent_purchase_rows(
    session: Session,
    user_id: str,
    limit: int = 10,
):
    statement = (
        select(StreamTransaction, Stream)
        .join(Stream, Stream.id == StreamTransaction.stream_id)
        .where(
            StreamTransaction.user_id == user_id,
            StreamTransaction.status.in_(tuple(CHARGE_SUCCESS_STATUSES)),
        )
        .order_by(StreamTransaction.created_at.desc())
        .limit(limit)
    )

    return session.exec(statement).all()


def build_stream_earnings_summary(
    session: Session,
    stream: Stream,
    transactions: list[StreamTransaction] | None = None,
):
    if transactions is None:
        transactions = list_transactions_for_stream(session, stream.id)

    access_setting = get_stream_access_setting(session, stream.id)
    access_type = (
        access_setting.access_type.value
        if access_setting
        else StreamAccessType.FREE.value
    )
    currency = access_setting.currency if access_setting else "usd"
    price_amount = access_setting.price_amount if access_setting else 0

    gross_sales_amount = 0
    platform_fees_amount = 0
    net_earnings_amount = 0
    refunded_amount = 0
    refund_pending_amount = 0

    successful_payment_count = 0
    refunded_payment_count = 0
    refund_pending_count = 0
    paid_viewer_ids: set[str] = set()

    last_payment_at: datetime | None = None

    for transaction in transactions:
        status = transaction.status

        if status in CHARGE_SUCCESS_STATUSES:
            successful_payment_count += 1
            gross_sales_amount += transaction.amount
            platform_fees_amount += transaction.platform_fee_amount

            payment_time = transaction.paid_at or transaction.created_at
            if payment_time and (last_payment_at is None or payment_time > last_payment_at):
                last_payment_at = payment_time

        if status in NET_EARNING_STATUSES:
            net_earnings_amount += transaction.broadcaster_amount
            paid_viewer_ids.add(transaction.user_id)

        if status == TransactionStatus.REFUNDED:
            refunded_payment_count += 1
            refunded_amount += transaction.amount

        if status == TransactionStatus.REFUND_PENDING:
            refund_pending_count += 1
            refund_pending_amount += transaction.amount

    return {
        "stream_id": stream.id,
        "currency": currency,
        "price_amount": price_amount,
        "access_type": access_type,
        "viewer_count": get_unique_viewer_count(session, stream.id),
        "successful_payment_count": successful_payment_count,
        "paid_viewer_count": len(paid_viewer_ids),
        "gross_sales_amount": gross_sales_amount,
        "platform_fees_amount": platform_fees_amount,
        "net_earnings_amount": net_earnings_amount,
        "refunded_amount": refunded_amount,
        "refund_pending_amount": refund_pending_amount,
        "refunded_payment_count": refunded_payment_count,
        "refund_pending_count": refund_pending_count,
        "last_payment_at": last_payment_at.isoformat() if last_payment_at else None,
        "updated_at": datetime.utcnow().isoformat(),
    }


def summarize_broadcaster_earnings(
    transactions: list[StreamTransaction],
    owned_streams: list[Stream],
    total_unique_viewers: int,
):
    live_stream_count = len(
        [stream for stream in owned_streams if stream.status == StreamStatus.LIVE]
    )
    ended_stream_count = len(
        [stream for stream in owned_streams if stream.status == StreamStatus.ENDED]
    )

    gross_sales_amount = 0
    platform_fees_amount = 0
    net_earnings_amount = 0
    refunded_amount = 0
    refund_pending_amount = 0

    successful_payment_count = 0
    refunded_payment_count = 0
    refund_pending_count = 0
    paid_viewer_ids: set[str] = set()

    for transaction in transactions:
        status = transaction.status

        if status in CHARGE_SUCCESS_STATUSES:
            successful_payment_count += 1
            gross_sales_amount += transaction.amount
            platform_fees_amount += transaction.platform_fee_amount

        if status in NET_EARNING_STATUSES:
            net_earnings_amount += transaction.broadcaster_amount
            paid_viewer_ids.add(transaction.user_id)

        if status == TransactionStatus.REFUNDED:
            refunded_payment_count += 1
            refunded_amount += transaction.amount

        if status == TransactionStatus.REFUND_PENDING:
            refund_pending_count += 1
            refund_pending_amount += transaction.amount

    return {
        "owned_stream_count": len(owned_streams),
        "live_stream_count": live_stream_count,
        "ended_stream_count": ended_stream_count,
        "total_unique_viewers": total_unique_viewers,
        "successful_payment_count": successful_payment_count,
        "paid_viewer_count": len(paid_viewer_ids),
        "gross_sales_amount": gross_sales_amount,
        "platform_fees_amount": platform_fees_amount,
        "net_earnings_amount": net_earnings_amount,
        "refunded_amount": refunded_amount,
        "refund_pending_amount": refund_pending_amount,
        "refunded_payment_count": refunded_payment_count,
        "refund_pending_count": refund_pending_count,
        "currency": "usd",
    }


def summarize_viewer_spend(
    transactions: list[StreamTransaction],
):
    successful_payment_count = 0
    purchased_stream_ids: set[str] = set()
    total_spent_amount = 0
    refunded_spend_amount = 0

    for transaction in transactions:
        status = transaction.status

        if status in CHARGE_SUCCESS_STATUSES:
            successful_payment_count += 1
            purchased_stream_ids.add(transaction.stream_id)

        if status in NET_EARNING_STATUSES:
            total_spent_amount += transaction.amount

        if status == TransactionStatus.REFUNDED:
            refunded_spend_amount += transaction.amount

    return {
        "successful_payment_count": successful_payment_count,
        "purchased_stream_count": len(purchased_stream_ids),
        "total_spent_amount": total_spent_amount,
        "refunded_spend_amount": refunded_spend_amount,
        "currency": "usd",
    }
