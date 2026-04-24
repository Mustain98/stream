from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.ws_ticket import verify_ws_ticket, consume_ws_ticket
from core.ws_manager import  manager
import json

router = APIRouter()


@router.websocket("/ws/stream/{stream_id}")
async def websocket_stream(websocket: WebSocket, stream_id: str):

    ticket = websocket.query_params.get("ticket")

    if not ticket:
        await websocket.close(code=1008)
        return

    data = verify_ws_ticket(ticket)

    if not data or data["stream_id"] != stream_id:
        await websocket.close(code=1008)
        return

    consume_ws_ticket(ticket)

    user_id = data["user_id"]
    role = data["role"]

    await websocket.accept()

    await manager.connect(stream_id, websocket, user_id, role)

    if role == "broadcaster":
        await manager.send_to_role(
            stream_id,
            "viewer",
            {
                "type": "broadcaster-ready",
                "from": user_id,
                "data": {"stream_id": stream_id},
            },
        )
    else:
        await manager.send_to_role(
            stream_id,
            "broadcaster",
            {
                "type": "viewer-ready",
                "from": user_id,
                "data": {"stream_id": stream_id},
            },
        )

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            msg_type = msg.get("type")

            # 🔥 ROLE ENFORCEMENT
            if role == "viewer" and msg_type == "offer":
                await websocket.send_json({"error": "Viewers cannot send offer"})
                continue

            if role == "broadcaster" and msg_type == "answer":
                await websocket.send_json({"error": "Broadcaster cannot send answer"})
                continue

            # 🔥 ROUTING LOGIC

            if msg_type == "offer":
                target_user = msg.get("to")
                payload = {
                    "type": "offer",
                    "from": user_id,
                    "data": msg.get("data")
                }
                if target_user:
                    payload["to"] = target_user
                    await manager.send_to_user(stream_id, target_user, payload)
                else:
                    await manager.send_to_role(stream_id, "viewer", payload)

            elif msg_type == "answer":
                target_user = msg.get("to")
                payload = {
                    "type": "answer",
                    "from": user_id,
                    "data": msg.get("data")
                }
                if target_user:
                    payload["to"] = target_user
                    await manager.send_to_user(stream_id, target_user, payload)
                else:
                    await manager.send_to_role(stream_id, "broadcaster", payload)

            elif msg_type == "ice":
                target_user = msg.get("to")
                payload = {
                    "type": "ice",
                    "from": user_id,
                    "data": msg.get("data")
                }
                if target_user:
                    payload["to"] = target_user
                    await manager.send_to_user(stream_id, target_user, payload)
                else:
                    await manager.broadcast(stream_id, payload, sender_ws=websocket)

            else:
                # fallback (chat etc.)
                await manager.broadcast(
                    stream_id,
                    {
                        "type": msg_type,
                        "from": user_id,
                        "data": msg.get("data")
                    },
                    sender_ws=websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(stream_id, websocket)

    except Exception as e:
        print("WS error:", e)
        manager.disconnect(stream_id, websocket)
