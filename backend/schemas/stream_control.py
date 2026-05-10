from typing import Optional

from sqlmodel import SQLModel


class BlockUserRequest(SQLModel):
    reason: Optional[str] = "blocked"


class UnblockUserRequest(SQLModel):
    reason: Optional[str] = "unblocked"