from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from schemas.stripe_payment import ReconcileCheckoutRequest
from controllers.stripe_controller import (
    create_stripe_checkout_controller,
    handle_stripe_webhook_controller,
    reconcile_checkout_session_controller,
)

router = APIRouter(tags=["stripe-payment"])


@router.post("/stream/{stream_id}/checkout")
def create_checkout_session(
    stream_id: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    response, error = create_stripe_checkout_controller(
        session=session,
        stream_id=stream_id,
        user_id=user.id,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    if error == "publisher_cannot_pay":
        raise HTTPException(status_code=400, detail="Publisher cannot pay for own stream")

    if error == "stream_is_free":
        raise HTTPException(status_code=400, detail="Stream is free")

    if error == "invalid_price":
        raise HTTPException(status_code=400, detail="Invalid stream price")

    if error == "broadcaster_not_connected":
        raise HTTPException(
            status_code=400,
            detail="Broadcaster has not connected a Stripe account",
        )

    if error == "broadcaster_onboarding_incomplete":
        raise HTTPException(
            status_code=400,
            detail="Broadcaster has not completed Stripe onboarding",
        )

    if error == "stripe_checkout_failed":
        raise HTTPException(
            status_code=502,
            detail="Could not create Stripe checkout session. Please try again.",
        )

    if error == "checkout_state_save_failed":
        raise HTTPException(
            status_code=500,
            detail="Checkout was created but local state could not be saved. Please retry.",
        )

    return response


@router.post("/payments/stripe/reconcile-checkout")
def reconcile_checkout_session(
    payload: ReconcileCheckoutRequest,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    response, error = reconcile_checkout_session_controller(
        session=session,
        checkout_session_id=payload.checkout_session_id,
        user_id=user.id,
    )

    if error == "transaction_not_found":
        raise HTTPException(status_code=404, detail="Transaction not found")

    if error == "not_allowed":
        raise HTTPException(status_code=403, detail="Not allowed")

    if error == "metadata_mismatch":
        raise HTTPException(status_code=400, detail="Stripe metadata mismatch")

    return response


@router.post("/payments/stripe/webhook")
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_session),
):
    response, error = await handle_stripe_webhook_controller(
        request=request,
        session=session,
    )

    if error == "missing_webhook_secret":
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET is not configured")

    if error == "invalid_payload":
        raise HTTPException(status_code=400, detail="Invalid payload")

    if error == "invalid_signature":
        raise HTTPException(status_code=400, detail="Invalid signature")

    if error == "metadata_mismatch":
        raise HTTPException(status_code=400, detail="Stripe webhook metadata mismatch")

    return response