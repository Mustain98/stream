from datetime import datetime

from sqlmodel import Session, select

from models import (
    StreamAccessSetting,
    StreamAccessType,
    StreamTransaction,
    TransactionStatus,
    StripeWebhookEvent,
)


def get_stream_access_setting(
    session: Session,
    stream_id: str,
):
    return session.exec(
        select(StreamAccessSetting).where(
            StreamAccessSetting.stream_id == stream_id,
        )
    ).first()


def create_default_access_setting(
    session: Session,
    stream_id: str,
):
    setting = StreamAccessSetting(
        stream_id=stream_id,
        access_type=StreamAccessType.FREE,
        price_amount=0,
        currency="usd",
        free_preview_seconds=0,
    )

    session.add(setting)

    return setting


def get_or_create_access_setting(
    session: Session,
    stream_id: str,
):
    setting = get_stream_access_setting(session, stream_id)

    if setting:
        return setting

    return create_default_access_setting(session, stream_id)


def update_access_setting(
    session: Session,
    setting: StreamAccessSetting,
    access_type: str,
    price_amount: int,
    currency: str,
    free_preview_seconds: int,
):
    if price_amount < 0:
        raise ValueError("price_amount cannot be negative")

    if free_preview_seconds < 0:
        raise ValueError("free_preview_seconds cannot be negative")

    setting.access_type = (
        StreamAccessType.PAID
        if access_type.lower() == "paid"
        else StreamAccessType.FREE
    )

    setting.price_amount = price_amount
    setting.currency = currency.lower()
    setting.free_preview_seconds = free_preview_seconds
    setting.updated_at = datetime.utcnow()

    session.add(setting)

    return setting


def get_paid_transaction(
    session: Session,
    stream_id: str,
    user_id: str,
):
    return session.exec(
        select(StreamTransaction).where(
            StreamTransaction.stream_id == stream_id,
            StreamTransaction.user_id == user_id,
            StreamTransaction.status == TransactionStatus.PAID,
        )
    ).first()


def has_paid_for_stream(
    session: Session,
    stream_id: str,
    user_id: str,
) -> bool:
    return get_paid_transaction(session, stream_id, user_id) is not None


def get_transaction(
    session: Session,
    transaction_id: str,
):
    return session.get(StreamTransaction, transaction_id)


def get_transaction_by_provider_session(
    session: Session,
    provider_session_id: str,
):
    return session.exec(
        select(StreamTransaction).where(
            StreamTransaction.provider_session_id == provider_session_id,
        )
    ).first()


def get_latest_checkout_transaction(
    session: Session,
    stream_id: str,
    user_id: str,
    provider: str = "stripe",
):
    """
    Only reuse rows where Stripe Checkout was actually created.
    Do not reuse PENDING rows with no provider_session_id.
    """
    return session.exec(
        select(StreamTransaction)
        .where(
            StreamTransaction.stream_id == stream_id,
            StreamTransaction.user_id == user_id,
            StreamTransaction.provider == provider,
            StreamTransaction.status == TransactionStatus.CHECKOUT_CREATED,
            StreamTransaction.provider_session_id != None,
        )
        .order_by(StreamTransaction.created_at.desc())
    ).first()


def get_stuck_pending_transactions_for_stream_user(
    session: Session,
    stream_id: str,
    user_id: str,
    provider: str = "stripe",
) -> list[StreamTransaction]:
    return session.exec(
        select(StreamTransaction).where(
            StreamTransaction.stream_id == stream_id,
            StreamTransaction.user_id == user_id,
            StreamTransaction.provider == provider,
            StreamTransaction.status == TransactionStatus.PENDING,
        )
    ).all()


def cancel_stuck_pending_transactions_for_stream_user(
    session: Session,
    stream_id: str,
    user_id: str,
    provider: str = "stripe",
) -> int:
    transactions = get_stuck_pending_transactions_for_stream_user(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        provider=provider,
    )

    for transaction in transactions:
        mark_transaction_cancelled(
            session=session,
            transaction=transaction,
            reason="stuck_pending_checkout_replaced",
        )

    return len(transactions)


def create_pending_transaction(
    session: Session,
    stream_id: str,
    user_id: str,
    broadcaster_id: str,
    amount: int,
    currency: str,
    provider: str = "manual",
    provider_session_id: str | None = None,
    platform_fee_amount: int = 0,
    broadcaster_amount: int = 0,
    stripe_transfer_destination: str | None = None,
    provider_idempotency_key: str | None = None,
):
    transaction = StreamTransaction(
        stream_id=stream_id,
        user_id=user_id,
        broadcaster_id=broadcaster_id,
        amount=amount,
        currency=currency.lower(),
        provider=provider,
        provider_session_id=provider_session_id,
        platform_fee_amount=platform_fee_amount,
        broadcaster_amount=broadcaster_amount,
        stripe_transfer_destination=stripe_transfer_destination,
        provider_idempotency_key=provider_idempotency_key,
        status=TransactionStatus.PENDING,
    )

    session.add(transaction)

    return transaction


def mark_transaction_checkout_created(
    session: Session,
    transaction: StreamTransaction,
    provider_session_id: str,
):
    transaction.provider_session_id = provider_session_id
    transaction.status = TransactionStatus.CHECKOUT_CREATED
    transaction.checkout_created_at = datetime.utcnow()

    session.add(transaction)

    return transaction


def set_transaction_provider_session(
    session: Session,
    transaction: StreamTransaction,
    provider_session_id: str,
):
    transaction.provider_session_id = provider_session_id

    session.add(transaction)

    return transaction


def mark_transaction_paid(
    session: Session,
    transaction: StreamTransaction,
    provider_payment_id: str | None = None,
):
    transaction.status = TransactionStatus.PAID
    transaction.provider_payment_id = provider_payment_id
    transaction.paid_at = datetime.utcnow()
    transaction.failure_reason = None

    session.add(transaction)

    return transaction


def mark_transaction_failed(
    session: Session,
    transaction: StreamTransaction,
    reason: str | None = None,
):
    transaction.status = TransactionStatus.FAILED
    transaction.failure_reason = reason

    session.add(transaction)

    return transaction


def mark_transaction_cancelled(
    session: Session,
    transaction: StreamTransaction,
    reason: str | None = None,
):
    transaction.status = TransactionStatus.CANCELLED
    transaction.failure_reason = reason

    session.add(transaction)

    return transaction


def cancel_transaction(
    session: Session,
    transaction: StreamTransaction,
):
    return mark_transaction_cancelled(
        session=session,
        transaction=transaction,
        reason="cancelled",
    )


def mark_transaction_refund_pending(
    session: Session,
    transaction: StreamTransaction,
    reason: str,
):
    transaction.status = TransactionStatus.REFUND_PENDING
    transaction.refund_reason = reason

    session.add(transaction)

    return transaction


def mark_transaction_refunded(
    session: Session,
    transaction: StreamTransaction,
    provider_refund_id: str | None,
    reason: str,
):
    transaction.status = TransactionStatus.REFUNDED
    transaction.provider_refund_id = provider_refund_id
    transaction.refund_reason = reason
    transaction.refunded_at = datetime.utcnow()

    session.add(transaction)

    return transaction


def mark_transaction_refund_failed(
    session: Session,
    transaction: StreamTransaction,
    reason: str,
):
    transaction.status = TransactionStatus.REFUND_FAILED
    transaction.refund_reason = reason

    session.add(transaction)

    return transaction


def has_processed_stripe_event(
    session: Session,
    stripe_event_id: str,
) -> bool:
    existing = session.exec(
        select(StripeWebhookEvent).where(
            StripeWebhookEvent.stripe_event_id == stripe_event_id
        )
    ).first()

    return existing is not None


def record_stripe_event_processed(
    session: Session,
    stripe_event_id: str,
    event_type: str,
    object_id: str | None = None,
):
    event = StripeWebhookEvent(
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        object_id=object_id,
    )

    session.add(event)

    return event