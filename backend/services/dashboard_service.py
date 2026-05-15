from services.earnings_service import (
    build_stream_earnings_summary,
    get_recent_purchase_rows,
    list_transactions_for_broadcaster,
    list_transactions_for_stream,
    list_transactions_for_viewer,
    summarize_broadcaster_earnings,
    summarize_viewer_spend,
)
from services.session_viewer import get_unique_viewer_count
from services.stream_service import list_owned_stream_records
from services.stripe_connect_account_service import get_stripe_connect_account_by_user_id


def build_stripe_status_payload(account):
    if not account:
        return None

    return {
        "connected": True,
        "stripe_account_id": account.stripe_account_id,
        "details_submitted": account.details_submitted,
        "charges_enabled": account.charges_enabled,
        "payouts_enabled": account.payouts_enabled,
        "onboarding_completed": account.onboarding_completed,
    }


def build_owned_stream_dashboard_items(session, owned_streams):
    stream_items = []
    total_unique_viewers = 0

    for stream in owned_streams:
        viewer_count = get_unique_viewer_count(session, stream.id)
        total_unique_viewers += viewer_count

        earnings_summary = build_stream_earnings_summary(
            session=session,
            stream=stream,
            transactions=list_transactions_for_stream(session, stream.id),
        )

        stream_items.append(
            {
                "id": stream.id,
                "title": stream.title,
                "description": stream.description,
                "status": stream.status.value,
                "broadcaster_id": stream.broadcaster_id,
                "started_at": stream.started_at,
                "viewer_count": viewer_count,
                "earnings_summary": earnings_summary,
            }
        )

    return stream_items, total_unique_viewers


def build_user_dashboard(session, user):
    owned_streams = list_owned_stream_records(session, user.id)
    owned_stream_items, total_unique_viewers = build_owned_stream_dashboard_items(
        session=session,
        owned_streams=owned_streams,
    )

    broadcaster_transactions = list_transactions_for_broadcaster(session, user.id)
    viewer_transactions = list_transactions_for_viewer(session, user.id)

    stripe_account = get_stripe_connect_account_by_user_id(session, user.id)
    recent_purchase_rows = get_recent_purchase_rows(session, user.id)

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at,
        },
        "stripe_status": build_stripe_status_payload(stripe_account),
        "broadcaster_stats": summarize_broadcaster_earnings(
            transactions=broadcaster_transactions,
            owned_streams=owned_streams,
            total_unique_viewers=total_unique_viewers,
        ),
        "viewer_stats": summarize_viewer_spend(viewer_transactions),
        "owned_streams": owned_stream_items,
        "recent_purchases": [
            {
                "transaction_id": transaction.id,
                "stream_id": stream.id,
                "stream_title": stream.title,
                "broadcaster_id": stream.broadcaster_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "status": transaction.status.value,
                "paid_at": transaction.paid_at,
                "created_at": transaction.created_at,
            }
            for transaction, stream in recent_purchase_rows
        ],
    }
