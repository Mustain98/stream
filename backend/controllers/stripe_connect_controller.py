from sqlmodel import Session

from services.stripe_connect_service import (
    create_express_account,
    create_account_onboarding_link,
    retrieve_connect_account,
)
from services.stripe_connect_account_service import (
    get_stripe_connect_account_by_user_id,
    create_stripe_connect_account_record,
    update_stripe_connect_account_status,
)


def create_broadcaster_onboarding_controller(
    session: Session,
    user,
):
    if not user.email:
        return None, "missing_email"

    connect_account = get_stripe_connect_account_by_user_id(
        session=session,
        user_id=str(user.id),
    )

    if not connect_account:
        stripe_account = create_express_account(email=user.email)

        connect_account = create_stripe_connect_account_record(
            session=session,
            user_id=str(user.id),
            stripe_account_id=stripe_account.id,
            account_type="express",
        )

        session.commit()
        session.refresh(connect_account)

    account_link = create_account_onboarding_link(
        stripe_account_id=connect_account.stripe_account_id,
    )

    return {
        "onboarding_url": account_link.url,
        "stripe_account_id": connect_account.stripe_account_id,
        "onboarding_completed": connect_account.onboarding_completed,
    }, None


def get_broadcaster_stripe_status_controller(
    session: Session,
    user,
):
    connect_account = get_stripe_connect_account_by_user_id(
        session=session,
        user_id=str(user.id),
    )

    if not connect_account:
        return {
            "connected": False,
            "stripe_account_id": None,
            "details_submitted": False,
            "charges_enabled": False,
            "payouts_enabled": False,
            "onboarding_completed": False,
        }, None

    stripe_account = retrieve_connect_account(
        connect_account.stripe_account_id
    )

    details_submitted = bool(stripe_account.details_submitted)
    charges_enabled = bool(stripe_account.charges_enabled)
    payouts_enabled = bool(stripe_account.payouts_enabled)

    update_stripe_connect_account_status(
        session=session,
        account=connect_account,
        details_submitted=details_submitted,
        charges_enabled=charges_enabled,
        payouts_enabled=payouts_enabled,
    )

    session.commit()
    session.refresh(connect_account)

    return {
        "connected": True,
        "stripe_account_id": connect_account.stripe_account_id,
        "details_submitted": connect_account.details_submitted,
        "charges_enabled": connect_account.charges_enabled,
        "payouts_enabled": connect_account.payouts_enabled,
        "onboarding_completed": connect_account.onboarding_completed,
    }, None