from fastapi import APIRouter, Depends, Request, HTTPException
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from core.dependencies import get_valid_stream
from models import Stream, User
from schemas.stripe_payment import ReconcileCheckoutRequest

from modules.payment.controllers.stripe_payment_controller import (
    create_stripe_checkout_controller,
    reconcile_checkout_session_controller,
)
from modules.payment.services.payment_flow_service import PaymentFlowError
from modules.payment.services.webhook_processing_service import process_stripe_webhook

router = APIRouter(tags=["stripe-payment"])


def handle_payment_error(e: PaymentFlowError):
    status_mapping = {
        "transaction_not_found": 404,
        "not_allowed": 403,
        "stripe_checkout_failed": 502,
        "checkout_state_save_failed": 500,
        "missing_webhook_secret": 500,
    }
    status_code = status_mapping.get(e.code, 400)
    raise HTTPException(status_code=status_code, detail=e.message)


@router.post("/stream/{stream_id}/checkout")
def create_checkout_session(
    stream: Stream = Depends(get_valid_stream),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    try:
        return create_stripe_checkout_controller(
            session=session,
            stream=stream,
            user_id=str(user.id),
        )
    except PaymentFlowError as e:
        handle_payment_error(e)


@router.post("/payments/stripe/reconcile-checkout")
def reconcile_checkout_session_route(
    payload: ReconcileCheckoutRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    try:
        return reconcile_checkout_session_controller(
            session=session,
            checkout_session_id=payload.checkout_session_id,
            user_id=str(user.id),
        )
    except PaymentFlowError as e:
        handle_payment_error(e)


@router.post("/payments/stripe/webhook")
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_session),
):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        return process_stripe_webhook(
            payload=payload,
            signature=signature,
            session=session,
        )
    except PaymentFlowError as e:
        handle_payment_error(e)