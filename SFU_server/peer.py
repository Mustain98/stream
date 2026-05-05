import uuid

from aiortc import RTCPeerConnection


class Peer:
    def __init__(self, role, room_id, websocket, user_id=None, username=None):
        self.id = str(uuid.uuid4())
        self.role = role
        self.room_id = room_id
        self.websocket = websocket

        self.user_id = user_id
        self.username = username or "Unknown"

        self.pc = None
        self.attached_kinds: set[str] = set()

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
        pc = self.pc

        if not pc:
            return

        self.pc = None

        try:
            if pc.connectionState != "closed":
                await pc.close()
        except Exception as e:
            print(f"[Peer {self.id}] close ignored error:", str(e))