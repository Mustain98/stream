import asyncio

from api.backend_client import backend_client


class PreviewManager:
    def __init__(self, cleanup_peer):
        self.cleanup_peer = cleanup_peer

    async def start_preview(self, peer, room):
        if not peer.is_preview:
            return

        await backend_client.preview_start(
            stream_id=room.room_id,
            user_id=str(peer.user_id),
        )

        peer.preview_task = asyncio.create_task(
            self._preview_timer(peer=peer, room=room)
        )

    async def end_preview(self, peer, room, reason: str):
        if not peer.is_preview:
            return

        if peer.preview_end_reported:
            return

        peer.preview_end_reported = True

        await backend_client.preview_end(
            stream_id=room.room_id,
            user_id=str(peer.user_id),
            reason=reason,
        )

    async def _preview_timer(self, peer, room):
        try:
            print(
                "[Preview] Timer started:",
                f"room={room.room_id}",
                f"user={peer.user_id}",
                f"seconds={peer.preview_seconds}",
            )

            await asyncio.sleep(peer.preview_seconds)

            if peer.id not in room.subscribers:
                return

            await peer.send_json(
                {
                    "type": "payment-required",
                    "reason": "preview_expired",
                    "message": "Preview ended. Please pay to continue watching.",
                    "streamId": room.room_id,
                }
            )

            await self.end_preview(peer, room, reason="preview_expired")

            await self.cleanup_peer(
                peer=peer,
                room=room,
                reason="preview_expired",
                close_websocket=True,
                report_preview_end=False,
            )

            print(
                "[Preview] Expired:",
                f"room={room.room_id}",
                f"user={peer.user_id}",
            )

        except asyncio.CancelledError:
            pass

        except Exception as exc:
            print("[Preview] Timer error:", str(exc))
