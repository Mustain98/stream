from fastapi import APIRouter, Header, HTTPException

from core.config import SFU_INTERNAL_SECRET
from models import EarningsUpdateRequest, KickUserRequest, UnblockUserRequest
from state import rooms

router = APIRouter()


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


@router.post("/internal/kick-user")
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


@router.post("/internal/unblock-user")
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


@router.post("/internal/earnings-update")
async def earnings_update(
    payload: EarningsUpdateRequest,
    x_sfu_secret: str | None = Header(default=None),
):
    verify_internal_secret(x_sfu_secret)

    print(
        "[SFU Earnings Update] received:",
        "stream_id=", payload.stream_id,
        "rooms=", list(rooms.keys()),
    )

    room = rooms.get(str(payload.stream_id))

    if not room:
        result = {
            "status": "ignored",
            "reason": "room_not_found",
            "stream_id": payload.stream_id,
            "active_rooms": list(rooms.keys()),
        }

        print("[SFU Earnings Update]", result)
        return result

    if not room.publisher:
        result = {
            "status": "ignored",
            "reason": "publisher_not_connected",
            "stream_id": payload.stream_id,
        }

        print("[SFU Earnings Update]", result)
        return result

    message = {
        "type": "earnings-update",
        "streamId": payload.stream_id,
        "summary": payload.earnings_summary,
    }

    delivered = await room.notify_publisher(message)

    result = {
        "status": "ok" if delivered else "ignored",
        "reason": None if delivered else "publisher_send_failed",
        "stream_id": payload.stream_id,
        "publisher_id": room.publisher.id if room.publisher else None,
    }

    print("[SFU Earnings Update]", result)

    return result
