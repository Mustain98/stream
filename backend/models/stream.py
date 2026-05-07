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
    JOIN = "join"
    LEAVE = "leave"
    START = "start"
    END = "end"



class Stream(SQLModel, table=True):
    __tablename__ = "streams"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    title: str
    description: Optional[str] = None

    status: StreamStatus = Field(default=StreamStatus.OFFLINE)

    broadcaster_id: str = Field(foreign_key="users.id", index=True)

    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    live_expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ViewerSession(SQLModel, table=True):
    __tablename__ = "viewer_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)

    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None

    is_active: bool = Field(default=True)



class StreamEvent(SQLModel, table=True):
    __tablename__ = "stream_events"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    stream_id: str = Field(foreign_key="streams.id", index=True)
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")

    event_type: EventType  # "join", "leave", "start", "end"

    message: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)