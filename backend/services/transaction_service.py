from datetime import datetime

from sqlmodel import Session, select

from models import (
    StreamAccessSetting,
    StreamAccessType,
    StreamTransaction,
    TransactionStatus,
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


def get_pending_transaction(
    session: Session,
    stream_id: str,
    user_id: str,
    provider: str = "stripe",
):
    return session.exec(
        select(StreamTransaction)
        .where(
            StreamTransaction.stream_id == stream_id,
            StreamTransaction.user_id == user_id,
            StreamTransaction.provider == provider,
            StreamTransaction.status == TransactionStatus.PENDING,
        )
        .order_by(StreamTransaction.created_at.desc())
    ).first()


def get_pending_transactions_for_stream_user(
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


def cancel_transaction(
    session: Session,
    transaction: StreamTransaction,
):
    transaction.status = TransactionStatus.CANCELLED

    session.add(transaction)

    return transaction


def cancel_pending_transactions_for_stream_user(
    session: Session,
    stream_id: str,
    user_id: str,
    provider: str = "stripe",
) -> int:
    pending_transactions = get_pending_transactions_for_stream_user(
        session=session,
        stream_id=stream_id,
        user_id=user_id,
        provider=provider,
    )

    for transaction in pending_transactions:
        cancel_transaction(session, transaction)

    return len(pending_transactions)


def create_pending_transaction(
    session: Session,
    stream_id: str,
    user_id: str,
    amount: int,
    currency: str,
    provider: str = "manual",
    provider_session_id: str | None = None,
):
    transaction = StreamTransaction(
        stream_id=stream_id,
        user_id=user_id,
        amount=amount,
        currency=currency.lower(),
        provider=provider,
        provider_session_id=provider_session_id,
        status=TransactionStatus.PENDING,
    )

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

    session.add(transaction)

    return transaction


def mark_transaction_failed(
    session: Session,
    transaction: StreamTransaction,
):
    transaction.status = TransactionStatus.FAILED

    session.add(transaction)

    return transaction


def mark_transaction_cancelled(
    session: Session,
    transaction: StreamTransaction,
):
    transaction.status = TransactionStatus.CANCELLED

    session.add(transaction)

    return transaction


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


def set_transaction_provider_session(
    session: Session,
    transaction: StreamTransaction,
    provider_session_id: str,
):
    transaction.provider_session_id = provider_session_id

    session.add(transaction)

    return transaction