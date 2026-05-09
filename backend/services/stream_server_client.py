import os

import httpx
from dotenv import load_dotenv

load_dotenv()

SFU_HTTP_URL = os.getenv("SFU_HTTP_URL", "http://localhost:7001")
SFU_INTERNAL_SECRET = os.getenv("SFU_INTERNAL_SECRET")


def get_sfu_headers():
    return {
        "X-SFU-Secret": SFU_INTERNAL_SECRET or "",
    }


async def kick_user_from_sfu(
    stream_id: str,
    user_id: str,
    reason: str = "blocked",
):
    if not SFU_INTERNAL_SECRET:
        print("[SFU Client] Missing SFU_INTERNAL_SECRET")
        return {
            "status": "ignored",
            "reason": "missing_sfu_internal_secret",
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{SFU_HTTP_URL}/internal/kick-user",
                headers=get_sfu_headers(),
                json={
                    "stream_id": stream_id,
                    "user_id": user_id,
                    "reason": reason,
                },
            )

            if response.status_code >= 400:
                print("[SFU Client] kick-user failed:", response.status_code, response.text)
                return {
                    "status": "failed",
                    "code": response.status_code,
                    "body": response.text,
                }

            return response.json()

    except Exception as e:
        print("[SFU Client] kick-user error:", str(e))
        return {
            "status": "failed",
            "reason": str(e),
        }


async def unblock_user_from_sfu(
    stream_id: str,
    user_id: str,
):
    if not SFU_INTERNAL_SECRET:
        print("[SFU Client] Missing SFU_INTERNAL_SECRET")
        return {
            "status": "ignored",
            "reason": "missing_sfu_internal_secret",
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{SFU_HTTP_URL}/internal/unblock-user",
                headers=get_sfu_headers(),
                json={
                    "stream_id": stream_id,
                    "user_id": user_id,
                },
            )

            if response.status_code >= 400:
                print("[SFU Client] unblock-user failed:", response.status_code, response.text)
                return {
                    "status": "failed",
                    "code": response.status_code,
                    "body": response.text,
                }

            return response.json()

    except Exception as e:
        print("[SFU Client] unblock-user error:", str(e))
        return {
            "status": "failed",
            "reason": str(e),
        }