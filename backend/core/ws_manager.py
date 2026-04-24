from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active = {}

    async def connect(self, stream_id, websocket, user_id, role):
        if stream_id not in self.active:
            self.active[stream_id] = []

        self.active[stream_id].append({
            "ws": websocket,
            "user_id": user_id,
            "role": role
        })

    def disconnect(self, stream_id, websocket):
        if stream_id in self.active:
            self.active[stream_id] = [
                c for c in self.active[stream_id]
                if c["ws"] != websocket
            ]

    async def send_to_role(self, stream_id, role, message):
        for conn in self.active.get(stream_id, []):
            if conn["role"] == role:
                await conn["ws"].send_json(message)

    async def send_to_user(self, stream_id, user_id, message):
        for conn in self.active.get(stream_id, []):
            if conn["user_id"] == user_id:
                await conn["ws"].send_json(message)

    async def broadcast(self, stream_id, message, sender_ws=None):
        for conn in self.active.get(stream_id, []):
            if conn["ws"] != sender_ws:
                await conn["ws"].send_json(message)


manager = ConnectionManager()
