from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

class StreamCreate(SQLModel):
    title: str
    description: str


class LiveStreamSummary(SQLModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    broadcaster_id: str
    started_at: Optional[datetime] = None
    viewer_count: int = 0
