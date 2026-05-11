import uuid
import asyncio
from aiortc import RTCPeerConnection


class Peer:
    def __init__(self,
        role,
        room_id, 
        websocket, 
        user_id=None, 
        username=None, 
        access_mode="free",
        preview_seconds=0
        ):

        self.id = str(uuid.uuid4())
        self.role = role
        self.room_id = room_id
        self.websocket = websocket

        self.user_id = user_id
        self.username = username or "Unknown"

        self.access_mode = access_mode or "free"
        self.preview_seconds = int(preview_seconds or 0)

        self.pc = None
        self.attached_kinds: set[str] = set()
        self.heartbeat_task=None
        self.preview_task=None

    async def create_peer_connection(self):
        pc = RTCPeerConnection()
        self.pc = pc

        @pc.on("connectionstatechange")
        async def on_connection_state_change():
            print(
                f"[Peer {self.id}] Connection state:",
                pc.connectionState,
            )

            if pc.connectionState in ["failed", "closed", "disconnected"]:
                await self.close()

        @pc.on("iceconnectionstatechange")
        async def on_ice_connection_state_change():
            print(
                f"[Peer {self.id}] ICE state:",
                pc.iceConnectionState,
            )

    async def send_json(self, message: dict):
        await self.websocket.send_json(message)

    async def close(self):
        current_task = asyncio.current_task()

        if self.heartbeat_task and self.heartbeat_task is not current_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None

        if self.preview_task and self.preview_task is not current_task:
            self.preview_task.cancel()
            self.preview_task = None

        pc = self.pc

        if not pc:
            return

        self.pc = None

        try:
            if pc.connectionState != "closed":
                await pc.close()
        except Exception as e:
            print(f"[Peer {self.id}] close ignored error:", str(e))