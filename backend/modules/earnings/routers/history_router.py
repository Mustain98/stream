from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from models import User
from modules.earnings.controllers.earnings_controller import (
    get_broadcaster_earnings_history_controller,
    get_viewer_spend_history_controller,
)

router = APIRouter(prefix="/auth", tags=["earnings-history"])


@router.get("/earnings/history")
def broadcaster_earnings_history(
    year: int | None = Query(default=None, ge=2020, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return get_broadcaster_earnings_history_controller(
        session=session,
        user_id=str(user.id),
        year=year,
        month=month,
    )


@router.get("/spend/history")
def viewer_spend_history(
    year: int | None = Query(default=None, ge=2020, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return get_viewer_spend_history_controller(
        session=session,
        user_id=str(user.id),
        year=year,
        month=month,
    )
