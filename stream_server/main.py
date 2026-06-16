from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import FRONTEND_ORIGIN
from routers.internal_router import router as internal_router
from routers.ws_router import router as ws_router

app = FastAPI(title="Custom Python SFU Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(internal_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    from state import rooms
    return {
        "message": "Custom Python SFU Server is running",
        "rooms": list(rooms.keys()),
    }


@app.get("/rooms")
async def list_rooms():
    from state import rooms
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
