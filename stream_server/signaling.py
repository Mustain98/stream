from fastapi import WebSocket, WebSocketDisconnect
from aiortc import RTCSessionDescription
from aiortc.sdp import candidate_from_sdp
from sfu_auth import verify_sfu_ticket

from models import (
    SignalType,
    PeerRole,
    parse_signal_message,
)
import asyncio

from backend_client import (
    heartbeat_publisher,
    SFU_HEARTBEAT_INTERVAL_SECONDS,
)
from peer import Peer

class SignalingServer:
    def __init__(self, rooms: dict, media_router, get_or_create_room, remove_room_if_empty):
        self.rooms = rooms
        self.media_router = media_router
        self.get_or_create_room = get_or_create_room
        self.remove_room_if_empty = remove_room_if_empty

    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()

        peer = None
        room = None

        try:
            raw_join_msg = await websocket.receive_json()
            join_msg = parse_signal_message(raw_join_msg)

            if join_msg.type != SignalType.JOIN:
                await websocket.send_json({
                    "type": "error",
                    "message": "First message must be join"
                })
                return

            payload=verify_sfu_ticket(join_msg.token)

            if not payload:
                await websocket.send_json({
                    "type":"error",
                    "message":"Invalid or Expired SFU token"
                })
                await websocket.close()
                return
            
            room_id = str(payload["stream_id"])
            role = payload["role"]
            user_id = str(payload["sub"])
            username = payload.get("username") or "Unknown"

            room = self.get_or_create_room(room_id)

            peer = Peer(
                role=role,
                room_id=room_id,
                websocket=websocket,
                user_id=user_id,
                username=username,
            )

            await peer.create_peer_connection()

            if role == PeerRole.PUBLISHER:
                if room.publisher is not None:
                    await peer.send_json({
                        "type": "error",
                        "message": "Room already has a publisher"
                    })
                    await peer.close()
                    return

                room.set_publisher(peer)
                await self.start_publisher_heartbeat(peer, room)
                self.setup_publisher_track_handler(peer, room)

                await peer.send_json({
                    "type": "info",
                    "message": "Joined as publisher",
                    "peerId": peer.id,
                    "roomId": room_id,
                })

                await room.broadcast_presence()
                await room.broadcast_stream_state()

                print(f"[Signaling] Publisher joined room {room_id}")

            elif role == PeerRole.SUBSCRIBER:
                room.add_subscriber(peer)

                # Existing publisher tracks are attached before answer creation.
                await self.media_router.attach_existing_tracks_to_subscriber(room, peer)

                await peer.send_json({
                    "type": "info",
                    "message": "Joined as subscriber",
                    "peerId": peer.id,
                    "roomId": room_id,
                })

                await room.broadcast_presence()
                await room.broadcast_stream_state()
                
                print(f"[Signaling] Subscriber joined room {room_id}")

            while True:
                raw_msg = await websocket.receive_json()
                msg = parse_signal_message(raw_msg)
                await self.handle_message(peer, room, msg)

        except WebSocketDisconnect:
            print("[Signaling] WebSocket disconnected")

        except Exception as e:
            print("[Signaling] Error:", str(e))

            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
            except Exception:
                pass

        finally:
            if peer and room:
                room.remove_peer(peer.id)
                await peer.close()

                if not room.is_empty():
                    await room.broadcast_presence()
                self.remove_room_if_empty(room.room_id)

    async def handle_message(self, peer, room, msg):
        if msg.type == SignalType.OFFER:
            await self.handle_offer(peer, room, msg)

        elif msg.type == SignalType.ICE:
            await self.handle_ice(peer, msg)

        elif msg.type == SignalType.LEAVE:
            await self.handle_leave(peer, room)

        elif msg.type == SignalType.STREAM_STATE:
            await self.handle_stream_state(peer, room, msg)

    async def handle_offer(self, peer, room, msg):
        """
        Browser sends offer.
        SFU replies with answer.
        """

        offer = RTCSessionDescription(
            sdp=msg.sdp,
            type="offer",
        )

        await peer.pc.setRemoteDescription(offer)

        # Important for subscribers:
        # If tracks already exist, attach them before creating answer.
        if peer.role == PeerRole.SUBSCRIBER:
            await self.media_router.attach_existing_tracks_to_subscriber(room, peer)

        answer = await peer.pc.createAnswer()
        await peer.pc.setLocalDescription(answer)

        await peer.send_json({
            "type": "answer",
            "sdp": peer.pc.localDescription.sdp,
        })

        print(f"[Signaling] Sent answer to {peer.role} {peer.id}")

    async def handle_ice(self, peer, msg):
        """
        Browser sends ICE candidate.

        aiortc expects parsed candidate objects, not the raw browser candidate string.
        """

        if msg.candidate is None:
            try:
                await peer.pc.addIceCandidate(None)
            except Exception as e:
                print(f"[Signaling] End-of-candidates ignored: {e}")
            return

        candidate_text = msg.candidate.candidate

        if candidate_text.startswith("candidate:"):
            candidate_text = candidate_text.split(":", 1)[1]

        candidate = candidate_from_sdp(candidate_text)
        candidate.sdpMid = msg.candidate.sdpMid
        candidate.sdpMLineIndex = msg.candidate.sdpMLineIndex

        await peer.pc.addIceCandidate(candidate)

    async def handle_leave(self, peer, room):
        room.remove_peer(peer.id)
        await peer.close()
        self.remove_room_if_empty(room.room_id)

    def setup_publisher_track_handler(self, peer, room):
        """
        When publisher sends audio/video tracks, route them to viewers.
        """

        @peer.pc.on("track")
        async def on_track(track):
            print(f"[Signaling] Publisher track received: {track.kind}")

            await self.media_router.handle_publisher_track(room, track)

            @track.on("ended")
            async def on_ended():
                print(f"[Signaling] Publisher track ended: {track.kind}")
    
    async def handle_stream_state(self, peer, room, msg):
        # SECURITY: only verified publisher can change stream state.
        if peer.role != PeerRole.PUBLISHER.value:
            await peer.send_json({
                "type": "error",
                "message": "Only publisher can change stream state",
            })
            return

        if msg.state not in ["paused", "live"]:
            await peer.send_json({
                "type": "error",
                "message": "Invalid stream state",
            })
            return

        room.stream_state = msg.state

        if hasattr(room, "broadcast_stream_state"):
            await room.broadcast_stream_state()

        print(f"[Room {room.room_id}] Stream state changed to {msg.state}")

    async def start_publisher_heartbeat(self, peer, room):
        async def heartbeat_loop():
            # Send immediately once publisher is accepted.
            await heartbeat_publisher(room.room_id)

            while True:
                await asyncio.sleep(SFU_HEARTBEAT_INTERVAL_SECONDS)
                await heartbeat_publisher(room.room_id)

        peer.heartbeat_task = asyncio.create_task(heartbeat_loop())


        