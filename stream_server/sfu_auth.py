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

    Expected required payload:
      type = sfu_ticket
      sub
      stream_id
      username
      role

    Optional access payload:
      access_mode = free | paid | preview
      preview_seconds = int
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

    except JWTError as e:
        print("[SFU Auth] Invalid ticket:", str(e))
        return None