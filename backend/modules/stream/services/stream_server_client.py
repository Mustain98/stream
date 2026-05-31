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


def post_internal_sfu(
    path: str,
    payload: dict,
):
    if not SFU_INTERNAL_SECRET:
        print("[SFU Client] Missing SFU_INTERNAL_SECRET")
        return {
            "status": "ignored",
            "reason": "missing_sfu_internal_secret",
        }

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{SFU_HTTP_URL}{path}",
                headers=get_sfu_headers(),
                json=payload,
            )

        if response.status_code >= 400:
            print("[SFU Client] internal request failed:", path, response.status_code, response.text)
            return {
                "status": "failed",
                "code": response.status_code,
                "body": response.text,
            }

        return response.json()

    except Exception as e:
        print("[SFU Client] internal request error:", path, str(e))
        return {
            "status": "failed",
            "reason": str(e),
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


def notify_earnings_update_in_sfu(
    stream_id: str,
    earnings_summary: dict,
):
    return post_internal_sfu(
        "/internal/earnings-update",
        {
            "stream_id": stream_id,
            "earnings_summary": earnings_summary,
        },
    )
