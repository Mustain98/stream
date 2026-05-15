from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class StreamPreviewUsage(SQLModel, table=True):
    __tablename__ = "previews"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)

    preview_limit_seconds: int
    used_seconds: int = 0

    active_started_at: Optional[datetime] = None
    exhausted_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)