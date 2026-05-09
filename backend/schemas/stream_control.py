from typing import Optional

from sqlmodel import SQLModel


class BlockUserRequest(SQLModel):
    reason: Optional[str] = "blocked"

class UnblockUserRequest(SQLModel):
    reason: Optional[str] = "unblocked"
    
class BlockUserResponse(SQLModel):
    status: str
    stream_id: str
    user_id: str
    reason: Optional[str] = None