from datetime import datetime
from typing import Optional
import enum
import uuid

from sqlalchemy import Index, text, UniqueConstraint
from sqlmodel import SQLModel, Field


class StreamAccessType(str, enum.Enum):
    FREE = "free"
    PAID = "paid"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    CHECKOUT_CREATED = "checkout_created"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    REFUND_FAILED = "refund_failed"


class TransferStatus(str, enum.Enum):
    NOT_TRANSFERRED = "not_transferred"
    TRANSFERRED = "transferred"
    TRANSFER_FAILED = "transfer_failed"


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
        UniqueConstraint(
            "provider_session_id",
            name="uq_stream_transactions_provider_session_id",
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    broadcaster_id: str = Field(foreign_key="users.id", index=True)

    amount: int
    currency: str = Field(default="usd")

    platform_fee_amount: int = Field(default=0)
    broadcaster_amount: int = Field(default=0)

    status: TransactionStatus = Field(default=TransactionStatus.PENDING)

    provider: str = Field(default="manual")

    provider_session_id: Optional[str] = Field(default=None, index=True)
    provider_payment_id: Optional[str] = Field(default=None, index=True)
    provider_refund_id: Optional[str] = Field(default=None, index=True)

    provider_idempotency_key: Optional[str] = Field(default=None, index=True, unique=True)

    stripe_transfer_destination: Optional[str] = Field(default=None, index=True)

    provider_transfer_id: Optional[str] = Field(default=None, index=True)
    transfer_status: TransferStatus = Field(default=TransferStatus.NOT_TRANSFERRED)

    failure_reason: Optional[str] = None
    refund_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    checkout_created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    transferred_at: Optional[datetime] = None


class StripeWebhookEvent(SQLModel, table=True):
    __tablename__ = "stripe_webhook_events"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stripe_event_id: str = Field(index=True, unique=True)
    event_type: str = Field(index=True)
    object_id: Optional[str] = Field(default=None, index=True)

    processed_at: datetime = Field(default_factory=datetime.utcnow)
