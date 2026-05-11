from datetime import datetime
from typing import Optional
import enum
import uuid

from sqlalchemy import Index, text
from sqlmodel import SQLModel, Field


class StreamAccessType(str, enum.Enum):
    FREE = "free"
    PAID = "paid"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class StreamAccessSetting(SQLModel, table=True):
    __tablename__ = "stream_access_settings"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True, unique=True)

    access_type: StreamAccessType = Field(default=StreamAccessType.FREE)

    price_amount: int = Field(default=0)
    currency: str = Field(default="usd")

    free_preview_seconds: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class StreamTransaction(SQLModel, table=True):
    __tablename__ = "stream_transactions"

    __table_args__ = (
        Index(
            "idx_unique_paid_stream_transaction",
            "stream_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'PAID'"),
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)

    amount: int
    currency: str = Field(default="usd")

    status: TransactionStatus = Field(default=TransactionStatus.PENDING)

    provider: str = Field(default="manual")
    provider_session_id: Optional[str] = Field(default=None, index=True)
    provider_payment_id: Optional[str] = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None