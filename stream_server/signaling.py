import asyncio

from aiortc import RTCSessionDescription
from aiortc.sdp import candidate_from_sdp
from fastapi import WebSocket, WebSocketDisconnect

from backend_client import backend_client
from config import SFU_HEARTBEAT_INTERVAL_SECONDS
from models import PeerRole, SignalType, parse_signal_message
from peer import Peer
from preview_manager import PreviewManager
from sfu_auth import verify_sfu_ticket
import re
import config

class SignalingServer:
    def __init__(self, rooms: dict, media_router, get_or_create_room, remove_room_if_empty):
        self.rooms = rooms
        self.media_router = media_router
        self.get_or_create_room = get_or_create_room
        self.remove_room_if_empty = remove_room_if_empty
        self.preview_manager = PreviewManager(cleanup_peer=self.cleanup_peer)

        # To add chat later, add SignalType.CHAT: self.handle_chat here.
        self.message_handlers = {
            SignalType.OFFER: self.handle_offer,
            SignalType.ICE: self.handle_ice,
            SignalType.LEAVE: self.handle_leave,
            SignalType.STREAM_STATE: self.handle_stream_state,
            SignalType.CHAT: self.handle_chat,
        }

    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()

        peer = None
        room = None

        try:
            raw_join_msg = await websocket.receive_json()
            join_msg = parse_signal_message(raw_join_msg)

            if join_msg.type != SignalType.JOIN:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "First message must be join",
                    }
                )
                await websocket.close()
                return

            payload = verify_sfu_ticket(join_msg.token)

            if not payload:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid or expired SFU token",
                    }
                )
                await websocket.close()
                return

            peer, room = await self.join_from_ticket(websocket, payload)

            while True:
                raw_msg = await websocket.receive_json()
                msg = parse_signal_message(raw_msg)
                await self.handle_message(peer, room, msg)

        except WebSocketDisconnect:
            print("[Signaling] WebSocket disconnected")

        except Exception as exc:
            print("[Signaling] Error:", str(exc))

            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": str(exc),
                    }
                )
            except Exception:
                pass

        finally:
            if peer and room:
                await self.cleanup_peer(
                    peer=peer,
                    room=room,
                    reason="websocket_disconnected",
                    close_websocket=False,
                    report_preview_end=True,
                )

    async def join_from_ticket(self, websocket: WebSocket, payload: dict):
        room_id = str(payload["stream_id"])
        role = str(payload["role"])
        user_id = str(payload["sub"])
        username = payload.get("username") or "Unknown"
        access_mode = payload.get("access_mode", "free")
        preview_seconds = int(payload.get("preview_seconds", 0) or 0)

        room = self.get_or_create_room(room_id)

        if role == PeerRole.SUBSCRIBER.value and room.is_user_blocked(user_id):
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "You are blocked from this stream.",
                }
            )
            await websocket.close()
            raise RuntimeError("blocked")

        peer = Peer(
            role=role,
            room_id=room_id,
            websocket=websocket,
            user_id=user_id,
            username=username,
            access_mode=access_mode,
            preview_seconds=preview_seconds,
        )

        await peer.create_peer_connection()

        if role == PeerRole.PUBLISHER.value:
            await self.join_publisher(peer, room)
            return peer, room

        if role == PeerRole.SUBSCRIBER.value:
            await self.join_subscriber(peer, room)
            return peer, room

        await peer.send_json(
            {
                "type": "error",
                "message": "Invalid role",
            }
        )
        await peer.close(close_websocket=True)
        raise RuntimeError("invalid_role")

    async def join_publisher(self, peer: Peer, room):
        if room.publisher is not None:
            await peer.send_json(
                {
                    "type": "error",
                    "message": "Room already has a publisher",
                }
            )
            await peer.close(close_websocket=True)
            raise RuntimeError("room_already_has_publisher")

        room.set_publisher(peer)
        await self.start_publisher_heartbeat(peer, room)
        self.setup_publisher_track_handler(peer, room)

        await peer.send_json(
            {
                "type": "info",
                "message": "Joined as publisher",
                "peerId": peer.id,
                "roomId": room.room_id,
            }
        )

        await room.broadcast_presence()
        await room.broadcast_stream_state()

        print(f"[Signaling] Publisher joined room {room.room_id}")

    async def join_subscriber(self, peer: Peer, room):
        room.add_subscriber(peer)
        await self.media_router.attach_existing_tracks_to_subscriber(room, peer)

        await peer.send_json(
            {
                "type": "info",
                "message": "Joined as subscriber",
                "peerId": peer.id,
                "roomId": room.room_id,
                "accessMode": peer.access_mode,
                "previewSeconds": peer.preview_seconds,
            }
        )

        await room.broadcast_presence()
        await room.broadcast_stream_state()

        if peer.is_preview:
            await self.preview_manager.start_preview(peer, room)

        print(
            f"[Signaling] Subscriber joined room {room.room_id} "
            f"access={peer.access_mode} preview={peer.preview_seconds}s"
        )

    async def handle_message(self, peer: Peer, room, msg):
        handler = self.message_handlers.get(msg.type)

        if not handler:
            await peer.send_json(
                {
                    "type": "error",
                    "message": f"Unsupported message type: {msg.type}",
                }
            )
            return

        await handler(peer, room, msg)

    async def handle_offer(self, peer: Peer, room, msg):
        offer = RTCSessionDescription(sdp=msg.sdp, type="offer")
        await peer.pc.setRemoteDescription(offer)

        if peer.role == PeerRole.SUBSCRIBER.value:
            await self.media_router.attach_existing_tracks_to_subscriber(room, peer)

        answer = await peer.pc.createAnswer()
        await peer.pc.setLocalDescription(answer)

        await peer.send_json(
            {
                "type": "answer",
                "sdp": peer.pc.localDescription.sdp,
            }
        )

        print(f"[Signaling] Sent answer to {peer.role} {peer.id}")

    async def handle_ice(self, peer: Peer, room, msg):
        if msg.candidate is None:
            try:
                await peer.pc.addIceCandidate(None)
            except Exception as exc:
                print(f"[Signaling] End-of-candidates ignored: {exc}")
            return

        candidate_text = msg.candidate.candidate

        if candidate_text.startswith("candidate:"):
            candidate_text = candidate_text.split(":", 1)[1]

        candidate = candidate_from_sdp(candidate_text)
        candidate.sdpMid = msg.candidate.sdpMid
        candidate.sdpMLineIndex = msg.candidate.sdpMLineIndex

        await peer.pc.addIceCandidate(candidate)

    async def handle_leave(self, peer: Peer, room, msg):
        await self.cleanup_peer(
            peer=peer,
            room=room,
            reason="viewer_left",
            close_websocket=True,
            report_preview_end=True,
        )

    async def handle_stream_state(self, peer: Peer, room, msg):
        if peer.role != PeerRole.PUBLISHER.value:
            await peer.send_json(
                {
                    "type": "error",
                    "message": "Only publisher can change stream state",
                }
            )
            return

        if msg.state not in ["paused", "live"]:
            await peer.send_json(
                {
                    "type": "error",
                    "message": "Invalid stream state",
                }
            )
            return

        room.stream_state = msg.state
        await room.broadcast_stream_state()

        print(f"[Room {room.room_id}] Stream state changed to {msg.state}")

    async def handle_chat(self, peer: Peer, room, msg):
        clean_message=(msg.message or"").strip()
        if not clean_message:
            await peer.send_json(
                {
                    "type":"error",
                    "message":"Chat message cannot be empty",
                }
            )
            return
        if len(clean_message)>config.Max_MSG_LEN:
            await peer.send_json(
                {
                "type": "error",
                "message": "Chat message is too long",
                }
            )
            return
        mentioned_usernames=extract_mentions(clean_message)
        mentioned_peers=room.find_peers_by_usernames(mentioned_usernames)
        mentions=[
            {
                "peerId":mentioned_peer.id,
                "userId":mentioned_peer.user_id,
                "username":mentioned_peer.username,
                "role":mentioned_peer.role,
            }
            for mentioned_peer in mentioned_peers
        ]
        await room.broadcast(
        {
            "type": "chat",
            "roomId": room.room_id,
            "peerId": peer.id,
            "userId": peer.user_id,
            "username": peer.username,
            "role": peer.role,
            "message": clean_message,
            "mentions": mentions,
        }
        )

        for mentioned_peer in mentioned_peers:
            if mentioned_peer.user_id ==peer.user_id:
                continue

            await mentioned_peer.send_json(
            {
                "type": "mention-notification",
                "roomId": room.room_id,
                "fromPeerId": peer.id,
                "fromUserId": peer.user_id,
                "fromUsername": peer.username,
                "message": clean_message,
            }
            )

    def setup_publisher_track_handler(self, peer: Peer, room):
        @peer.pc.on("track")
        async def on_track(track):
            print(f"[Signaling] Publisher track received: {track.kind}")
            await self.media_router.handle_publisher_track(room, track)

            @track.on("ended")
            async def on_ended():
                print(f"[Signaling] Publisher track ended: {track.kind}")

    async def start_publisher_heartbeat(self, peer: Peer, room):
        async def heartbeat_loop():
            await backend_client.heartbeat_publisher(room.room_id)

            while True:
                await asyncio.sleep(SFU_HEARTBEAT_INTERVAL_SECONDS)
                await backend_client.heartbeat_publisher(room.room_id)

        peer.heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def cleanup_peer(
        self,
        peer: Peer,
        room,
        reason: str,
        close_websocket: bool = False,
        report_preview_end: bool = True,
    ):
        if report_preview_end and peer.is_preview:
            await self.preview_manager.end_preview(peer, room, reason=reason)

        room.remove_peer(peer.id)
        await peer.close(close_websocket=close_websocket)

        if not room.is_empty():
            await room.broadcast_presence()

        self.remove_room_if_empty(room.room_id)

MENTION_PATTERN = re.compile(r"@([a-zA-Z0-9_]{1,32})")


def extract_mentions(message: str) -> list[str]:
    usernames = MENTION_PATTERN.findall(message or "")

    seen = set()
    unique_usernames = []

    for username in usernames:
        key = username.lower()

        if key not in seen:
            seen.add(key)
            unique_usernames.append(username)

    return unique_usernames