import calendar
from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, select

from models import (
    Stream,
    StreamAccessType,
    StreamStatus,
    StreamTransaction,
    TransactionStatus,
)
from modules.viewer.services.session_service import get_unique_viewer_count
from modules.payment.services.transaction_service import get_stream_access_setting

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


# ── private helpers ──────────────────────────────────────────────────────────

def _month_key(t: StreamTransaction) -> str:
    return (t.paid_at or t.created_at).strftime("%Y-%m")


def _day_key(t: StreamTransaction) -> str:
    return (t.paid_at or t.created_at).strftime("%Y-%m-%d")


def _get_labels(year: int, month: int | None) -> list[str]:
    if month:
        _, days = calendar.monthrange(year, month)
        return [f"{year:04d}-{month:02d}-{d:02d}" for d in range(1, days + 1)]
    return [f"{year:04d}-{m:02d}" for m in range(1, 13)]


def _filter_by_period(
    transactions: list[StreamTransaction],
    year: int,
    month: int | None,
) -> list[StreamTransaction]:
    out = []
    for t in transactions:
        dt = t.paid_at or t.created_at
        if dt.year != year:
            continue
        if month and dt.month != month:
            continue
        out.append(t)
    return out


def _bucket(
    transactions: list[StreamTransaction],
    month: int | None,
) -> dict[str, list[StreamTransaction]]:
    buckets: dict[str, list[StreamTransaction]] = defaultdict(list)
    key_fn = _day_key if month else _month_key
    for t in transactions:
        buckets[key_fn(t)].append(t)
    return dict(buckets)


def _agg_broadcaster(transactions: list[StreamTransaction]) -> dict:
    gross = platform = net = refunded = refund_pending = 0
    successful = refunded_count = refund_pending_count = 0
    viewer_ids: set[str] = set()

    for t in transactions:
        s = t.status
        if s in CHARGE_SUCCESS_STATUSES:
            successful += 1
            gross += t.amount
            platform += t.platform_fee_amount
        if s in NET_EARNING_STATUSES:
            net += t.broadcaster_amount
            viewer_ids.add(t.user_id)
        if s == TransactionStatus.REFUNDED:
            refunded_count += 1
            refunded += t.amount
        if s == TransactionStatus.REFUND_PENDING:
            refund_pending_count += 1
            refund_pending += t.amount

    return {
        "gross_sales_amount": gross,
        "platform_fees_amount": platform,
        "net_earnings_amount": net,
        "refunded_amount": refunded,
        "refund_pending_amount": refund_pending,
        "successful_payment_count": successful,
        "paid_viewer_count": len(viewer_ids),
        "refunded_payment_count": refunded_count,
        "refund_pending_count": refund_pending_count,
    }


def _agg_viewer(transactions: list[StreamTransaction]) -> dict:
    total_spent = refunded = successful = 0
    stream_ids: set[str] = set()

    for t in transactions:
        s = t.status
        if s in CHARGE_SUCCESS_STATUSES:
            successful += 1
            stream_ids.add(t.stream_id)
        if s in NET_EARNING_STATUSES:
            total_spent += t.amount
        if s == TransactionStatus.REFUNDED:
            refunded += t.amount

    return {
        "total_spent_amount": total_spent,
        "refunded_amount": refunded,
        "successful_payment_count": successful,
        "streams_purchased": len(stream_ids),
    }


def _broadcaster_graph(labels: list[str], buckets: dict) -> dict:
    gross_sales, net_earnings, refunds = [], [], []
    for label in labels:
        a = _agg_broadcaster(buckets.get(label, []))
        gross_sales.append(a["gross_sales_amount"])
        net_earnings.append(a["net_earnings_amount"])
        refunds.append(a["refunded_amount"])
    return {
        "labels": labels,
        "series": {
            "gross_sales": gross_sales,
            "net_earnings": net_earnings,
            "refunds": refunds,
        },
    }


def _viewer_graph(labels: list[str], buckets: dict) -> dict:
    total_spent, refunds = [], []
    for label in labels:
        a = _agg_viewer(buckets.get(label, []))
        total_spent.append(a["total_spent_amount"])
        refunds.append(a["refunded_amount"])
    return {
        "labels": labels,
        "series": {
            "total_spent": total_spent,
            "refunds": refunds,
        },
    }


# ── public history builders ───────────────────────────────────────────────────

def build_broadcaster_earnings_history(
    transactions: list[StreamTransaction],
    year: int | None = None,
    month: int | None = None,
) -> dict:
    now = datetime.utcnow()
    year = year or now.year
    labels = _get_labels(year, month)
    filtered = _filter_by_period(transactions, year, month)
    buckets = _bucket(filtered, month)

    breakdown = sorted(
        [{"period": lbl, **_agg_broadcaster(buckets.get(lbl, []))} for lbl in labels if lbl in buckets],
        key=lambda x: x["period"],
        reverse=True,
    )

    return {
        "view": "daily" if month else "monthly",
        "period": f"{year:04d}-{month:02d}" if month else str(year),
        "summary": _agg_broadcaster(filtered),
        "breakdown": breakdown,
        "graph": _broadcaster_graph(labels, buckets),
        "currency": "usd",
    }


def build_viewer_spend_history(
    transactions: list[StreamTransaction],
    year: int | None = None,
    month: int | None = None,
) -> dict:
    now = datetime.utcnow()
    year = year or now.year
    labels = _get_labels(year, month)
    filtered = _filter_by_period(transactions, year, month)
    buckets = _bucket(filtered, month)

    breakdown = sorted(
        [{"period": lbl, **_agg_viewer(buckets.get(lbl, []))} for lbl in labels if lbl in buckets],
        key=lambda x: x["period"],
        reverse=True,
    )

    return {
        "view": "daily" if month else "monthly",
        "period": f"{year:04d}-{month:02d}" if month else str(year),
        "summary": _agg_viewer(filtered),
        "breakdown": breakdown,
        "graph": _viewer_graph(labels, buckets),
        "currency": "usd",
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
