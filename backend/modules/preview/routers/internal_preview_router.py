from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db.session import get_session
from core.dependencies import verify_sfu_internal_secret
from modules.preview.services.preview_service import (
    start_preview_session,
    end_preview_session,
)
from modules.payment.services.transaction_service import get_or_create_access_setting


router = APIRouter(prefix="/internal/sfu", tags=["internal-sfu-preview"])


class PreviewStartPayload(BaseModel):
    stream_id: str
    user_id: str


class PreviewEndPayload(BaseModel):
    stream_id: str
    user_id: str
    reason: str | None = None


@router.post("/preview/start")
def internal_preview_start(
    payload: PreviewStartPayload,
    session: Session = Depends(get_session),
    _=Depends(verify_sfu_internal_secret),
):
    setting = get_or_create_access_setting(session, payload.stream_id)

    remaining = start_preview_session(
        session=session,
        stream_id=payload.stream_id,
        user_id=payload.user_id,
        preview_limit_seconds=setting.free_preview_seconds,
    )

    if remaining <= 0:
        raise HTTPException(status_code=402, detail="preview_exhausted")

    return {
        "ok": True,
        "remaining_preview": remaining,
    }


@router.post("/preview/end")
def internal_preview_end(
    payload: PreviewEndPayload,
    session: Session = Depends(get_session),
    _=Depends(verify_sfu_internal_secret),
):
    remaining = end_preview_session(
        session=session,
        stream_id=payload.stream_id,
        user_id=payload.user_id,
    )

    return {
        "ok": True,
        "remaining_preview": remaining,
        "reason": payload.reason,
    }
