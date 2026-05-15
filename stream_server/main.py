from fastapi import FastAPI, Header, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config import FRONTEND_ORIGIN, SFU_INTERNAL_SECRET
from media_router import MediaRouter
from models import KickUserRequest, UnblockUserRequest
from room import Room
from signaling import SignalingServer

app = FastAPI(title="Custom Python SFU Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms: dict[str, Room] = {}


def verify_internal_secret(x_sfu_secret: str | None):
    if not SFU_INTERNAL_SECRET:
        raise HTTPException(
            status_code=500,
            detail="SFU_INTERNAL_SECRET is not configured",
        )

    if x_sfu_secret != SFU_INTERNAL_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid internal secret",
        )


def get_or_create_room(room_id: str):
    if room_id not in rooms:
        rooms[room_id] = Room(room_id)
        print(f"[Main] Created room: {room_id}")

    return rooms[room_id]


def remove_room_if_empty(room_id: str):
    room = rooms.get(room_id)

    if room and room.is_empty():
        del rooms[room_id]
        print(f"[Main] Removed empty room: {room_id}")


media_router = MediaRouter()

signaling_server = SignalingServer(
    rooms=rooms,
    media_router=media_router,
    get_or_create_room=get_or_create_room,
    remove_room_if_empty=remove_room_if_empty,
)


@app.get("/")
async def root():
    return {
        "message": "Custom Python SFU Server is running",
        "rooms": list(rooms.keys()),
    }


@app.get("/rooms")
async def list_rooms():
    result = {}

    for room_id, room in rooms.items():
        result[room_id] = {
            "hasPublisher": room.publisher is not None,
            "subscriberCount": len(room.subscribers),
            "tracks": list(room.tracks.keys()),
            "blockedUsers": list(room.blocked_user_ids),
            "streamState": room.stream_state,
        }

    return result


@app.post("/internal/kick-user")
async def kick_user_from_room(
    payload: KickUserRequest,
    x_sfu_secret: str | None = Header(default=None),
):
    verify_internal_secret(x_sfu_secret)

    room = rooms.get(payload.stream_id)

    if not room:
        return {
            "status": "ignored",
            "reason": "room_not_found",
            "stream_id": payload.stream_id,
            "user_id": payload.user_id,
            "kicked": 0,
        }

    room.block_user(payload.user_id)

    kicked_count = await room.kick_user(
        user_id=payload.user_id,
        reason=payload.reason,
    )

    print(
        "[Internal] Kick user:",
        "room=", payload.stream_id,
        "user_id=", payload.user_id,
        "kicked=", kicked_count,
    )

    return {
        "status": "ok",
        "stream_id": payload.stream_id,
        "user_id": payload.user_id,
        "kicked": kicked_count,
    }


@app.post("/internal/unblock-user")
async def unblock_user_from_room(
    payload: UnblockUserRequest,
    x_sfu_secret: str | None = Header(default=None),
):
    verify_internal_secret(x_sfu_secret)

    room = rooms.get(payload.stream_id)

    if not room:
        return {
            "status": "ignored",
            "reason": "room_not_found",
            "stream_id": payload.stream_id,
            "user_id": payload.user_id,
        }

    room.unblock_user(payload.user_id)

    print(
        "[Internal] Unblock user:",
        "room=", payload.stream_id,
        "user_id=", payload.user_id,
    )

    return {
        "status": "ok",
        "stream_id": payload.stream_id,
        "user_id": payload.user_id,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await signaling_server.handle_websocket(websocket)