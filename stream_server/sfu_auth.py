from typing import Optional

from jose import JWTError, jwt

from config import ALGORITHM, SECRET_KEY


VALID_ROLES = {"publisher", "subscriber"}
VALID_ACCESS_MODES = {"free", "paid", "preview"}


def verify_sfu_ticket(token: Optional[str]):
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        print("[SFU Auth] Invalid ticket:", str(exc))
        return None

    if payload.get("type") != "sfu_ticket":
        return None

    if not payload.get("sub"):
        return None

    if not payload.get("stream_id"):
        return None

    if payload.get("role") not in VALID_ROLES:
        return None

    access_mode = payload.get("access_mode", "free")

    if access_mode not in VALID_ACCESS_MODES:
        return None

    try:
        preview_seconds = int(payload.get("preview_seconds", 0) or 0)
    except Exception:
        return None

    if preview_seconds < 0:
        return None

    payload["username"] = payload.get("username") or "Unknown"
    payload["access_mode"] = access_mode
    payload["preview_seconds"] = preview_seconds

    return payload