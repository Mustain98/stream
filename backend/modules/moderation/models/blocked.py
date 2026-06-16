from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class StreamBlocked(SQLModel, table=True):
    __tablename__ = "stream_blocked"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)

    reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
