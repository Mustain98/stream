from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from schemas.transaction import (
    StreamAccessSettingsUpdate,
    CreateManualTransactionRequest,
)
from controllers.transaction_controller import (
    get_stream_access_controller,
    update_stream_access_settings_controller,
    create_manual_paid_transaction_controller,
)

router = APIRouter(prefix="/stream", tags=["transaction"])


@router.get("/{stream_id}/access")
def get_stream_access(
    stream_id: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    response, error = get_stream_access_controller(
        session=session,
        stream_id=stream_id,
        user_id=user.id,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    return response


@router.patch("/{stream_id}/access-settings")
def update_stream_access_settings(
    stream_id: str,
    payload: StreamAccessSettingsUpdate,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    response, error = update_stream_access_settings_controller(
        session=session,
        stream_id=stream_id,
        broadcaster_id=user.id,
        payload=payload,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    if error == "not_allowed":
        raise HTTPException(status_code=403, detail="Not allowed")

    if error == "invalid_price":
        raise HTTPException(status_code=400, detail="Paid stream must have a price")

    if error == "invalid_preview":
        raise HTTPException(status_code=400, detail="Preview seconds cannot be negative")

    if error == "stripe_not_connected":
        raise HTTPException(
            status_code=400,
            detail="Connect Stripe before making this stream paid",
        )

    if error == "stripe_onboarding_incomplete":
        raise HTTPException(
            status_code=400,
            detail="Complete Stripe onboarding before making this stream paid",
        )

    return response


@router.post("/{stream_id}/transactions/manual-paid")
def create_manual_paid_transaction(
    stream_id: str,
    payload: CreateManualTransactionRequest,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    response, error = create_manual_paid_transaction_controller(
        session=session,
        stream_id=stream_id,
        current_user_id=user.id,
        payload=payload,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    if error == "stream_is_free":
        raise HTTPException(status_code=400, detail="Stream is free")

    return response