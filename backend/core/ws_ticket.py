# backend/core/ws_ticket.py

import os
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

SFU_TICKET_EXPIRE_SECONDS = 120


def create_sfu_ticket(user_id: str, stream_id: str, role: str, username:Optional[str]=None):
    """
    Create a short-lived signed token for joining the SFU server.

    This token is created by the main backend and verified by the SFU server.
    """

    expire = datetime.utcnow() + timedelta(seconds=SFU_TICKET_EXPIRE_SECONDS)

    payload = {
        "sub": str(user_id),
        "stream_id": str(stream_id),
        "role": role,
        "type": "sfu_ticket",
        "username":username,
        "exp": expire,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_sfu_ticket(token: str):
    """
    Optional verification function.
    Main backend may use this for debugging.
    SFU server should also have the same verification logic.
    """

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "sfu_ticket":
            return None

        return payload

    except JWTError:
        return None