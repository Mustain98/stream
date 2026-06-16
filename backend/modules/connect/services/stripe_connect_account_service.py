from datetime import datetime

from sqlmodel import Session, select

from models import StripeConnectAccount


def get_stripe_connect_account_by_user_id(
    session: Session,
    user_id: str,
):
    return session.exec(
        select(StripeConnectAccount).where(
            StripeConnectAccount.user_id == user_id
        )
    ).first()


def get_stripe_connect_account_by_stripe_id(
    session: Session,
    stripe_account_id: str,
):
    return session.exec(
        select(StripeConnectAccount).where(
            StripeConnectAccount.stripe_account_id == stripe_account_id
        )
    ).first()


def create_stripe_connect_account_record(
    session: Session,
    user_id: str,
    stripe_account_id: str,
    account_type: str = "express",
):
    account = StripeConnectAccount(
        user_id=user_id,
        stripe_account_id=stripe_account_id,
        account_type=account_type,
        details_submitted=False,
        charges_enabled=False,
        payouts_enabled=False,
        onboarding_completed=False,
    )

    session.add(account)

    return account


def update_stripe_connect_account_status(
    session: Session,
    account: StripeConnectAccount,
    details_submitted: bool,
    charges_enabled: bool,
    payouts_enabled: bool,
):
    account.details_submitted = details_submitted
    account.charges_enabled = charges_enabled
    account.payouts_enabled = payouts_enabled
    account.onboarding_completed = (
        details_submitted
        and charges_enabled
        and payouts_enabled
    )
    account.updated_at = datetime.utcnow()

    session.add(account)

    return account
