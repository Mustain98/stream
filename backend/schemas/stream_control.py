from typing import Optional

from sqlmodel import SQLModel


class BlockUserRequest(SQLModel):
    reason: str


class UnblockUserRequest(SQLModel):
    reason: Optional[str] = "unblocked"