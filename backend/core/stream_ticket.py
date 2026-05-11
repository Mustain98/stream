import os
from typing import Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
SFU_TICKET_EXPIRE_SECONDS = int(os.getenv("SFU_TICKET_EXPIRE_SECONDS", "120"))


def create_sfu_ticket(
    user_id: str,
    stream_id: str,
    role: str,
    username: Optional[str] = None,
    access_mode: str = "free",
    preview_seconds: int = 0,
):
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")

    if role not in ["publisher", "subscriber"]:
        raise ValueError("Invalid SFU role")

    if access_mode not in ["free", "paid", "preview"]:
        raise ValueError("Invalid access mode")

    if preview_seconds < 0:
        raise ValueError("preview_seconds cannot be negative")

    expire = datetime.utcnow() + timedelta(seconds=SFU_TICKET_EXPIRE_SECONDS)

    payload = {
        "sub": str(user_id),
        "stream_id": str(stream_id),
        "role": role,
        "type": "sfu_ticket",
        "username": username,
        "access_mode": access_mode,
        "preview_seconds": int(preview_seconds),
        "exp": expire,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_sfu_ticket(token: str):
    if not SECRET_KEY:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "sfu_ticket":
            return None

        if not payload.get("sub"):
            return None

        if not payload.get("stream_id"):
            return None

        if payload.get("role") not in ["publisher", "subscriber"]:
            return None

        access_mode = payload.get("access_mode", "free")

        if access_mode not in ["free", "paid", "preview"]:
            return None

        preview_seconds = payload.get("preview_seconds", 0)

        try:
            preview_seconds = int(preview_seconds or 0)
        except Exception:
            return None

        if preview_seconds < 0:
            return None

        payload["access_mode"] = access_mode
        payload["preview_seconds"] = preview_seconds

        return payload

    except JWTError:
        return None