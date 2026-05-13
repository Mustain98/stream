from typing import Optional

from sqlmodel import SQLModel


class StreamAccessSettingsUpdate(SQLModel):
    access_type: str = "free"
    price_amount: int = 0
    currency: str = "usd"
    free_preview_seconds: int = 0


class StreamAccessResponse(SQLModel):
    stream_id: str
    access_type: str
    price_amount: int
    currency: str
    free_preview_seconds: int
    has_paid: bool
    can_watch: bool
    access_mode: str


class CreateManualTransactionRequest(SQLModel):
    user_id: Optional[str] = None


class TransactionResponse(SQLModel):
    id: str
    stream_id: str
    user_id: str
    broadcaster_id: str
    amount: int
    currency: str
    platform_fee_amount: int
    broadcaster_amount: int
    status: str
    provider: str