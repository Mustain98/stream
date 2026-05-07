from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from room import Room
from media_router import MediaRouter
from signaling import SignalingServer


app = FastAPI(title="Custom Python SFU Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


rooms = {}


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
        }

    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await signaling_server.handle_websocket(websocket)