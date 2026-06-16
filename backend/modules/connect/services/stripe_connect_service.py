import os

import stripe
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def create_express_account(email: str):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    account = stripe.Account.create(
        type="express",
        email=email,
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
    )

    return account


def create_account_onboarding_link(stripe_account_id: str):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    account_link = stripe.AccountLink.create(
        account=stripe_account_id,
        refresh_url=f"{FRONTEND_ORIGIN}/dashboard/stripe/refresh",
        return_url=f"{FRONTEND_ORIGIN}/dashboard/stripe/return",
        type="account_onboarding",
    )

    return account_link


def retrieve_connect_account(stripe_account_id: str):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    return stripe.Account.retrieve(stripe_account_id)
