import os

import httpx
from dotenv import load_dotenv

load_dotenv()

MAIN_BACKEND_URL = os.getenv("MAIN_BACKEND_URL")
SFU_INTERNAL_SECRET = os.getenv("SFU_INTERNAL_SECRET")
SFU_HEARTBEAT_INTERVAL_SECONDS = int(
    os.getenv("SFU_HEARTBEAT_INTERVAL_SECONDS")
)


def get_headers():
    return {
        "X-SFU-Secret": SFU_INTERNAL_SECRET or "",
    }


async def heartbeat_publisher(stream_id: str):
    """
    Called by the SFU while the publisher is connected.

    This extends live_expires_at in the main backend.
    If the publisher disconnects, this heartbeat stops.
    Then the main backend cleanup loop eventually ends the stream.
    """

    if not SFU_INTERNAL_SECRET:
        print("[BackendClient] Missing SFU_INTERNAL_SECRET")
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{MAIN_BACKEND_URL}/internal/sfu/publisher-heartbeat/{stream_id}",
                headers=get_headers(),
            )

            if response.status_code >= 400:
                print(
                    "[BackendClient] publisher-heartbeat failed:",
                    response.status_code,
                    response.text,
                )

    except Exception as e:
        print("[BackendClient] publisher-heartbeat error:", str(e))