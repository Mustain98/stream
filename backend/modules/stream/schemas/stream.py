from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class StreamCreate(SQLModel):
    title: str
    description: str
    min_duration_seconds: int = Field(default=0, ge=0)
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None


class LiveStreamSummary(SQLModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    broadcaster_id: str
    broadcaster_username: Optional[str] = None
    started_at: Optional[datetime] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    viewer_count: int = 0
