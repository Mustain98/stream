from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import Index


class ViewerSession(SQLModel, table=True):
    __tablename__ = "viewer_sessions"

    __table_args__ = (
        Index(
            "idx_unique_active_viewer_session",
            "stream_id",
            "user_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)

    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None

    is_active: bool = Field(default=True)
