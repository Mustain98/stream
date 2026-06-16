from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
import enum


class StreamStatus(str, enum.Enum):
    OFFLINE = "offline"
    LIVE = "live"
    ENDED = "ended"


class EventType(str, enum.Enum):
    START = "start"
    END = "end"
    JOIN = "join"
    LEAVE = "leave"
    BLOCK = "block"
    UNBLOCK = "unblock"


class Stream(SQLModel, table=True):
    __tablename__ = "streams"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    title: str
    description: Optional[str] = None

    status: StreamStatus = Field(default=StreamStatus.OFFLINE)

    broadcaster_id: str = Field(foreign_key="users.id", index=True)
    min_duration_seconds: int = Field(default=0, ge=0)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    settlement_completed_at: Optional[datetime] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    live_expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StreamEvent(SQLModel, table=True):
    __tablename__ = "stream_events"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")

    event_type: EventType

    message: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
