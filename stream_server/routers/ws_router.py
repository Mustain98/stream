from fastapi import APIRouter, WebSocket

from sfu.media_router import MediaRouter
from signaling.handler import SignalingServer
from state import get_or_create_room, remove_room_if_empty, rooms

router = APIRouter()

media_router = MediaRouter()

signaling_server = SignalingServer(
    rooms=rooms,
    media_router=media_router,
    get_or_create_room=get_or_create_room,
    remove_room_if_empty=remove_room_if_empty,
)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await signaling_server.handle_websocket(websocket)
