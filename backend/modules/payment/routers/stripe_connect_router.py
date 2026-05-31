from fastapi import APIRouter, Depends
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from models import User
from modules.payment.controllers.stripe_connect_controller import (
    create_broadcaster_onboarding_controller,
    get_broadcaster_stripe_status_controller,
)

router = APIRouter(prefix="/stripe/connect", tags=["stripe-connect"])


@router.post("/onboard")
def create_broadcaster_onboarding(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return create_broadcaster_onboarding_controller(
        session=session,
        user=user,
    )


@router.get("/status")
def get_broadcaster_stripe_status(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return get_broadcaster_stripe_status_controller(
        session=session,
        user=user,
    )