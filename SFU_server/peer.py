import uuid
from typing import Optional, Set

from fastapi import WebSocket
from aiortc import RTCPeerConnection

class Peer:
    def __init__(self,role,room_id,websocket,user_id,username):
        self.id=str(uuid.uuid4())
        self.role=role
        self.room_id=room_id
        self.websocket=websocket
        # added user field to show viewer list
        self.user_id = user_id
        self.username= username
        self.pc=None

        self.attached_kinds:set[str] = set()

    async def create_peer_connection(self):
        self.pc=RTCPeerConnection()

        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            print(
                f"[Peer {self.id}] Connection state:",
                self.pc.connectionState,
            )

            if self.pc.connectionState in ["failed","closed","disconnected"]:
                await self.close()


        @self.pc.on("iceconnectionstatechange")
        async def on_ice_connection_state_change():
            print(
                f"[Peer {self.id}] ICE state:",
                self.pc.iceConnectionState,
            ) 


    async def send_json(self, message: dict):
        await self.websocket.send_json(message)
        
    async def close(self):
        if self.pc:
            try:
                if self.pc.connectionState != "closed":
                    await self.pc.close()
            except Exception as e:
                print(f"[Peer {self.id}] close ignored error:", str(e))
            finally:
                self.pc = None