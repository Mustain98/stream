from typing import Any

from pydantic import BaseModel


class KickUserRequest(BaseModel):
    stream_id: str
    user_id: str
    reason: str = "blocked"


class UnblockUserRequest(BaseModel):
    stream_id: str
    user_id: str


class EarningsUpdateRequest(BaseModel):
    stream_id: str
    earnings_summary: dict[str, Any]
