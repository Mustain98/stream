from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class StripeConnectAccount(SQLModel, table=True):
    __tablename__ = "stripe_connect_accounts"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # One Stripe Connect account per user/broadcaster
    user_id: str = Field(foreign_key="users.id", index=True, unique=True)

    # Stripe account id: acct_xxx
    stripe_account_id: str = Field(index=True, unique=True)

    account_type: str = Field(default="express")

    details_submitted: bool = Field(default=False)
    charges_enabled: bool = Field(default=False)
    payouts_enabled: bool = Field(default=False)

    onboarding_completed: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None