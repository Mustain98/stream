# SFU_server/sfu_auth.py

import os
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-this")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def verify_sfu_ticket(token: Optional[str]):
    """
    Verifies the signed SFU ticket created by the main backend.

    Returns payload if valid.
    Returns None if invalid/expired.
    """

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "sfu_ticket":
            return None

        if not payload.get("sub"):
            return None

        if not payload.get("stream_id"):
            return None
        
        if not payload.get("username"):
            return None

        if payload.get("role") not in ["publisher", "subscriber"]:
            return None

        return payload

    except JWTError as e:
        print("[SFU Auth] Invalid ticket:", str(e))
        return None