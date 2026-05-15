import httpx

from config import (
    MAIN_BACKEND_URL,
    SFU_INTERNAL_SECRET,
    get_internal_headers,
)


class BackendClient:
    def __init__(self):
        self.base_url = MAIN_BACKEND_URL.rstrip("/")

    async def post_internal(self, path: str, payload: dict | None = None):
        if not SFU_INTERNAL_SECRET:
            print("[BackendClient] Missing SFU_INTERNAL_SECRET")
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}{path}",
                    headers=get_internal_headers(),
                    json=payload,
                )

            if response.status_code >= 400:
                print(
                    "[BackendClient] internal request failed:",
                    path,
                    response.status_code,
                    response.text,
                )
                return None

            try:
                return response.json()
            except Exception:
                return None

        except Exception as exc:
            print("[BackendClient] internal request error:", path, str(exc))
            return None

    async def heartbeat_publisher(self, stream_id: str):
        return await self.post_internal(
            f"/internal/sfu/publisher-heartbeat/{stream_id}"
        )

    async def preview_start(self, stream_id: str, user_id: str):
        return await self.post_internal(
            "/internal/sfu/preview/start",
            {
                "stream_id": stream_id,
                "user_id": user_id,
            },
        )

    async def preview_end(self, stream_id: str, user_id: str, reason: str):
        return await self.post_internal(
            "/internal/sfu/preview/end",
            {
                "stream_id": stream_id,
                "user_id": user_id,
                "reason": reason,
            },
        )


backend_client = BackendClient()