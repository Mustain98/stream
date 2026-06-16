from fastapi import Depends, HTTPException, Header
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from models import Stream, User, StripeConnectAccount
from modules.stream.services.stream_service import get_stream
from modules.connect.services.stripe_connect_account_service import get_stripe_connect_account_by_user_id

import os
from dotenv import load_dotenv

load_dotenv()

SFU_INTERNAL_SECRET = os.getenv("SFU_INTERNAL_SECRET")



def get_valid_stream(
    stream_id: str,
    session: Session = Depends(get_session),
) -> Stream:
    stream = get_stream(session, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


def require_stream_broadcaster(
    stream: Stream = Depends(get_valid_stream),
    user: User = Depends(get_current_user),
) -> Stream:
    if str(stream.broadcaster_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not authorized or not the broadcaster")
    return stream


def require_stripe_onboarding(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StripeConnectAccount:
    connect_account = get_stripe_connect_account_by_user_id(session, str(user.id))
    
    if not connect_account:
        raise HTTPException(status_code=400, detail="Connect Stripe before performing this action")
        
    if not connect_account.onboarding_completed:
        raise HTTPException(status_code=400, detail="Complete Stripe onboarding before performing this action")
        
    if not connect_account.stripe_account_id:
        raise HTTPException(status_code=400, detail="Connect Stripe before performing this action")
        
    return connect_account


def verify_sfu_internal_secret(x_sfu_secret: str | None = Header(default=None)):
    if not SFU_INTERNAL_SECRET:
        raise HTTPException(
            status_code=500,
            detail="SFU_INTERNAL_SECRET is not configured",
        )

    if x_sfu_secret != SFU_INTERNAL_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid SFU internal secret",
        )

