from datetime import datetime

from sqlmodel import Session

from models import Stream, StreamTransaction, TransactionStatus, TransferStatus
from modules.earnings.services.earnings_relay_service import relay_stream_earnings_update
from modules.connect.services.stripe_connect_account_service import get_stripe_connect_account_by_user_id
from modules.payment.services.stripe_service import (
    create_refund_for_payment_intent,
    create_transfer_to_connected_account,
)
from modules.payment.services.transaction_service import (
    list_paid_not_transferred_transactions_for_stream,
    mark_transaction_refund_pending,
    mark_transaction_refunded,
    mark_transaction_refund_failed,
    mark_transaction_transferred,
    mark_transaction_transfer_failed,
)


def stripe_object_to_dict(obj):
    if isinstance(obj, dict):
        return obj

    try:
        return obj.to_dict_recursive()
    except AttributeError:
        pass

    try:
        return obj._to_dict_recursive()
    except AttributeError:
        pass

    return dict(obj)


def get_stream_duration_seconds(stream: Stream) -> int:
    if not stream.started_at or not stream.ended_at:
        return 0

    return int((stream.ended_at - stream.started_at).total_seconds())


def settle_stream_payment_after_end(session: Session, stream: Stream) -> dict:
    if stream.settlement_completed_at is not None:
        return {"action": "already_settled"}

    duration_seconds = get_stream_duration_seconds(stream)
    min_duration_seconds = stream.min_duration_seconds or 0

    if duration_seconds < min_duration_seconds:
        result = refund_paid_viewers_for_short_stream(
            session=session,
            stream=stream,
            duration_seconds=duration_seconds,
            min_duration_seconds=min_duration_seconds,
        )
    else:
        result = transfer_paid_viewers_to_broadcaster(
            session=session,
            stream=stream,
            duration_seconds=duration_seconds,
            min_duration_seconds=min_duration_seconds,
        )

    stream.settlement_completed_at = datetime.utcnow()
    session.add(stream)

    return result


def transfer_paid_viewers_to_broadcaster(
    session: Session,
    stream: Stream,
    duration_seconds: int,
    min_duration_seconds: int,
) -> dict:
    connect_account = get_stripe_connect_account_by_user_id(
        session=session,
        user_id=str(stream.broadcaster_id),
    )

    if not connect_account or not connect_account.stripe_account_id:
        return {
            "action": "transfer_failed",
            "reason": "broadcaster_stripe_account_missing",
            "duration_seconds": duration_seconds,
            "min_duration_seconds": min_duration_seconds,
            "transferred_count": 0,
            "failed_count": 0,
        }

    transactions = list_paid_not_transferred_transactions_for_stream(
        session=session,
        stream_id=stream.id,
    )

    transferred_count = 0
    failed_count = 0
    skipped_count = 0
    transferred_amount = 0
    errors: list[dict] = []

    for transaction in transactions:
        if transaction.transfer_status == TransferStatus.TRANSFERRED:
            skipped_count += 1
            continue

        if transaction.status != TransactionStatus.PAID:
            skipped_count += 1
            continue

        if transaction.broadcaster_amount <= 0:
            mark_transaction_transfer_failed(
                session=session,
                transaction=transaction,
                reason="broadcaster_amount_must_be_positive",
            )
            failed_count += 1
            continue

        try:
            transfer = create_transfer_to_connected_account(
                amount=transaction.broadcaster_amount,
                currency=transaction.currency,
                destination_account_id=connect_account.stripe_account_id,
                transaction_id=transaction.id,
                stream_id=stream.id,
                idempotency_key=f"transfer:{transaction.id}",
            )

            transfer_dict = stripe_object_to_dict(transfer)
            transfer_id = transfer_dict.get("id")

            if not transfer_id:
                raise ValueError("Stripe transfer response missing 'id'")

            mark_transaction_transferred(
                session=session,
                transaction=transaction,
                provider_transfer_id=transfer_id,
            )

            transferred_count += 1
            transferred_amount += transaction.broadcaster_amount

        except Exception as error:
            mark_transaction_transfer_failed(
                session=session,
                transaction=transaction,
                reason=f"stripe_transfer_failed:{str(error)}",
            )

            failed_count += 1
            errors.append(
                {
                    "transaction_id": transaction.id,
                    "error": str(error),
                }
            )

    relay_stream_earnings_update(session=session, stream_id=stream.id)

    return {
        "action": "transferred",
        "duration_seconds": duration_seconds,
        "min_duration_seconds": min_duration_seconds,
        "transferred_count": transferred_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "transferred_amount": transferred_amount,
        "errors": errors,
    }


def refund_paid_viewers_for_short_stream(
    session: Session,
    stream: Stream,
    duration_seconds: int,
    min_duration_seconds: int,
) -> dict:
    transactions = list_paid_not_transferred_transactions_for_stream(
        session=session,
        stream_id=stream.id,
    )

    refunded_count = 0
    failed_count = 0
    skipped_count = 0
    refunded_amount = 0
    reason = "stream_ended_before_minimum_duration"
    errors: list[dict] = []

    for transaction in transactions:
        if transaction.status != TransactionStatus.PAID:
            skipped_count += 1
            continue

        if transaction.transfer_status == TransferStatus.TRANSFERRED:
            mark_transaction_refund_failed(
                session=session,
                transaction=transaction,
                reason="cannot_auto_refund_after_transfer",
            )

            failed_count += 1
            errors.append(
                {
                    "transaction_id": transaction.id,
                    "error": "transaction already transferred",
                }
            )
            continue

        if not transaction.provider_payment_id:
            mark_transaction_refund_failed(
                session=session,
                transaction=transaction,
                reason="missing_provider_payment_id",
            )

            failed_count += 1
            errors.append(
                {
                    "transaction_id": transaction.id,
                    "error": "missing provider_payment_id",
                }
            )
            continue

        try:
            refund = create_refund_for_payment_intent(
                payment_intent_id=transaction.provider_payment_id,
            )
            refund_dict = stripe_object_to_dict(refund)
        except Exception as stripe_error:
            mark_transaction_refund_failed(
                session=session,
                transaction=transaction,
                reason=f"stripe_refund_failed:{str(stripe_error)}",
            )
            failed_count += 1
            errors.append({"transaction_id": transaction.id, "error": str(stripe_error)})
            continue

        mark_transaction_refund_pending(
            session=session,
            transaction=transaction,
            reason=reason,
        )
        mark_transaction_refunded(
            session=session,
            transaction=transaction,
            provider_refund_id=refund_dict.get("id"),
            reason=reason,
        )
        refunded_count += 1
        refunded_amount += transaction.amount

    relay_stream_earnings_update(session=session, stream_id=stream.id)

    return {
        "action": "refunded",
        "reason": reason,
        "duration_seconds": duration_seconds,
        "min_duration_seconds": min_duration_seconds,
        "refunded_count": refunded_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "refunded_amount": refunded_amount,
        "errors": errors,
    }


def settle_late_single_transaction(
    session: Session,
    stream: Stream,
    transaction: StreamTransaction,
) -> None:
    """
    Settle one transaction that became PAID after stream.settlement_completed_at was already set.
    This handles the race condition where the stream ended while the viewer's Stripe webhook was
    still in-flight — the main settlement run found zero PAID transactions and exited, but now
    the transaction is confirmed paid and must be individually refunded or transferred.
    """
    if transaction.status != TransactionStatus.PAID:
        return
    if transaction.transfer_status == TransferStatus.TRANSFERRED:
        return

    duration_seconds = get_stream_duration_seconds(stream)
    min_duration_seconds = stream.min_duration_seconds or 0

    if duration_seconds < min_duration_seconds:
        if not transaction.provider_payment_id:
            mark_transaction_refund_failed(
                session, transaction, "late_missing_provider_payment_id"
            )
        else:
            try:
                refund = create_refund_for_payment_intent(transaction.provider_payment_id)
                refund_dict = stripe_object_to_dict(refund)
                mark_transaction_refund_pending(
                    session, transaction, "late_payment_stream_ended_early"
                )
                mark_transaction_refunded(
                    session,
                    transaction,
                    refund_dict.get("id"),
                    "late_payment_stream_ended_early",
                )
            except Exception as e:
                mark_transaction_refund_failed(
                    session, transaction, f"late_stripe_refund_failed:{str(e)}"
                )
    else:
        connect_account = get_stripe_connect_account_by_user_id(
            session, str(stream.broadcaster_id)
        )
        if not connect_account or not connect_account.stripe_account_id:
            mark_transaction_transfer_failed(
                session, transaction, "late_broadcaster_stripe_account_missing"
            )
        elif transaction.broadcaster_amount <= 0:
            mark_transaction_transfer_failed(
                session, transaction, "late_broadcaster_amount_must_be_positive"
            )
        else:
            try:
                transfer = create_transfer_to_connected_account(
                    amount=transaction.broadcaster_amount,
                    currency=transaction.currency,
                    destination_account_id=connect_account.stripe_account_id,
                    transaction_id=transaction.id,
                    stream_id=stream.id,
                    idempotency_key=f"transfer:{transaction.id}",
                )
                transfer_dict = stripe_object_to_dict(transfer)
                mark_transaction_transferred(
                    session, transaction, transfer_dict.get("id")
                )
            except Exception as e:
                mark_transaction_transfer_failed(
                    session, transaction, f"late_stripe_transfer_failed:{str(e)}"
                )

    session.commit()
    relay_stream_earnings_update(session=session, stream_id=stream.id)
