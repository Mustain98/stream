from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


def gen_id():
    return str(uuid.uuid4())


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    username: str = Field(index=True, unique=True)
    email: Optional[str] = Field(default=None, index=True)

    password_hash: str

    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)