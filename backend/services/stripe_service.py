import os

import stripe
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def create_stream_checkout_session(
    stream_id: str,
    user_id: str,
    transaction_id: str,
    title: str,
    amount: int,
    currency: str,
):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    success_url = (
        f"{FRONTEND_ORIGIN}/watch/{stream_id}"
        f"?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    )

    cancel_url = f"{FRONTEND_ORIGIN}/watch/{stream_id}?payment=cancelled"

    session = stripe.checkout.Session.create(
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[
            {
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {
                        "name": f"Access to stream: {title}",
                    },
                    "unit_amount": amount,
                },
                "quantity": 1,
            }
        ],
        metadata={
            "stream_id": stream_id,
            "user_id": user_id,
            "transaction_id": transaction_id,
        },
    )

    return session