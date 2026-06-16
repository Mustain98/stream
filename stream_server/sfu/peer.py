import asyncio
import uuid

from aiortc import RTCPeerConnection


class Peer:
    def __init__(
        self,
        role: str,
        room_id: str,
        websocket,
        user_id: str | None = None,
        username: str | None = None,
        access_mode: str = "free",
        preview_seconds: int = 0,
    ):
        self.id = str(uuid.uuid4())
        self.role = role
        self.room_id = room_id
        self.websocket = websocket

        self.user_id = user_id
        self.username = username or "Unknown"

        self.access_mode = access_mode or "free"
        self.preview_seconds = int(preview_seconds or 0)
        self.preview_end_reported = False

        self.pc: RTCPeerConnection | None = None
        self.attached_kinds: set[str] = set()

        self.heartbeat_task: asyncio.Task | None = None
        self.preview_task: asyncio.Task | None = None

    @property
    def is_publisher(self) -> bool:
        return self.role == "publisher"

    @property
    def is_subscriber(self) -> bool:
        return self.role == "subscriber"

    @property
    def is_preview(self) -> bool:
        return (
            self.is_subscriber
            and self.access_mode == "preview"
            and self.preview_seconds > 0
        )

    async def create_peer_connection(self):
        pc = RTCPeerConnection()
        self.pc = pc

        @pc.on("connectionstatechange")
        async def on_connection_state_change():
            print(f"[Peer {self.id}] Connection state:", pc.connectionState)

        @pc.on("iceconnectionstatechange")
        async def on_ice_connection_state_change():
            print(f"[Peer {self.id}] ICE state:", pc.iceConnectionState)

        return pc

    async def send_json(self, message: dict):
        await self.websocket.send_json(message)

    def cancel_background_tasks(self):
        current_task = asyncio.current_task()

        for task_attr in ["heartbeat_task", "preview_task"]:
            task = getattr(self, task_attr)

            if task and task is not current_task:
                task.cancel()

            setattr(self, task_attr, None)

    async def close_peer_connection(self):
        pc = self.pc
        self.pc = None

        if not pc:
            return

        try:
            if pc.connectionState != "closed":
                await pc.close()
        except Exception as exc:
            print(f"[Peer {self.id}] close pc ignored error:", str(exc))

    async def close_websocket(self):
        try:
            await self.websocket.close()
        except Exception:
            pass

    async def close(self, close_websocket: bool = False):
        self.cancel_background_tasks()
        await self.close_peer_connection()

        if close_websocket:
            await self.close_websocket()
