from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from controllers.stripe_connect_controller import (
    create_broadcaster_onboarding_controller,
    get_broadcaster_stripe_status_controller,
)

router = APIRouter(prefix="/stripe/connect", tags=["stripe-connect"])


@router.post("/onboard")
def create_broadcaster_onboarding(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    response, error = create_broadcaster_onboarding_controller(
        session=session,
        user=user,
    )

    if error == "missing_email":
        raise HTTPException(
            status_code=400,
            detail="User email is required for Stripe onboarding",
        )

    return response


@router.get("/status")
def get_broadcaster_stripe_status(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    response, error = get_broadcaster_stripe_status_controller(
        session=session,
        user=user,
    )

    return response