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
    idempotency_key: str,
):
    """
    Creates Stripe Checkout Session.

    New flow:
    - viewer pays platform
    - no broadcaster transfer here
    - transfer happens later after stream ends normally
    """
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
        metadata={
            "stream_id": stream_id,
            "user_id": user_id,
            "broadcaster_id": broadcaster_id,
            "transaction_id": transaction_id,
        },
        payment_intent_data={
            "metadata": {
                "stream_id": stream_id,
                "user_id": user_id,
                "broadcaster_id": broadcaster_id,
                "transaction_id": transaction_id,
            }
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

    return stripe.PaymentIntent.retrieve(payment_intent_id)


def create_transfer_to_connected_account(
    amount: int,
    currency: str,
    destination_account_id: str,
    transaction_id: str,
    stream_id: str,
    idempotency_key: str,
):
    """
    One transaction = one Stripe transfer.
    Called only after normal stream end.
    """
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    if amount <= 0:
        raise ValueError("transfer amount must be greater than 0")

    return stripe.Transfer.create(
        amount=amount,
        currency=currency.lower(),
        destination=destination_account_id,
        transfer_group=f"stream_{stream_id}",
        metadata={
            "stream_id": stream_id,
            "transaction_id": transaction_id,
        },
        idempotency_key=idempotency_key,
    )


def create_refund_for_payment_intent(
    payment_intent_id: str,
    reason: str = "requested_by_customer",
):
    """
    Refunds viewer payment.

    Since money was not transferred yet, do not use:
    - reverse_transfer=True
    - refund_application_fee=True
    """
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    return stripe.Refund.create(
        payment_intent=payment_intent_id,
        reason=reason,
    )