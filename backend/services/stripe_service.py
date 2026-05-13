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
    broadcaster_id: str,
    transaction_id: str,
    title: str,
    amount: int,
    currency: str,
    broadcaster_stripe_account_id: str,
    platform_fee_amount: int,
    idempotency_key: str,
):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    success_url = (
        f"{FRONTEND_ORIGIN}/watch/{stream_id}"
        f"?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    )

    cancel_url = f"{FRONTEND_ORIGIN}/watch/{stream_id}?payment=cancelled"

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=transaction_id,
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
        payment_intent_data={
            "application_fee_amount": platform_fee_amount,
            "transfer_data": {
                "destination": broadcaster_stripe_account_id,
            },
        },
        metadata={
            "stream_id": stream_id,
            "user_id": user_id,
            "broadcaster_id": broadcaster_id,
            "transaction_id": transaction_id,
        },
        idempotency_key=idempotency_key,
    )

    return checkout_session


def retrieve_checkout_session(checkout_session_id: str):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    return stripe.checkout.Session.retrieve(checkout_session_id)


def retrieve_payment_intent(payment_intent_id: str):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    return stripe.PaymentIntent.retrieve(
        payment_intent_id,
        expand=[
            "latest_charge",
            "latest_charge.transfer",
        ],
    )


def create_refund_for_payment_intent(
    payment_intent_id: str,
    reason: str = "requested_by_customer",
):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    return stripe.Refund.create(
        payment_intent=payment_intent_id,
        reverse_transfer=True,
        refund_application_fee=True,
        reason=reason,
    )