from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class UserCreate(SQLModel):
    username: str
    password: str
    email: Optional[str] = None


class UserLogin(SQLModel):
    username: str
    password: str


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(SQLModel):
    id: str
    username: str
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
