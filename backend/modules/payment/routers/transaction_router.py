from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from models import Stream, User
from schemas.transaction import StreamAccessSettingsUpdate
from modules.payment.controllers.transaction_controller import (
    get_stream_access_controller,
    update_stream_access_settings_controller,
)
from core.dependencies import get_valid_stream, require_stream_broadcaster, require_stripe_onboarding

router = APIRouter(prefix="/stream", tags=["transaction"])


@router.get("/{stream_id}/access")
def get_stream_access(
    stream: Stream = Depends(get_valid_stream),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return get_stream_access_controller(
        session=session,
        stream=stream,
        user_id=str(user.id) if user else None,
    )


@router.patch("/{stream_id}/access-settings")
def update_stream_access_settings(
    payload: StreamAccessSettingsUpdate,
    stream: Stream = Depends(require_stream_broadcaster),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if payload.access_type.lower() == "paid":
        if payload.price_amount <= 0:
            raise HTTPException(status_code=400, detail="Paid stream must have a price")
            
        # Verify stripe onboarding via dependency
        require_stripe_onboarding(user, session)

    if payload.free_preview_seconds < 0:
        raise HTTPException(status_code=400, detail="Preview seconds cannot be negative")

    return update_stream_access_settings_controller(
        session=session,
        stream=stream,
        payload=payload,
    )

