from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class UserCreate(SQLModel):
    username: str
    password: str


class UserLogin(SQLModel):
    username: str
    password: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(SQLModel):
    id: str
    username: str
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
