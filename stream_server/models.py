from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    JOIN = "join"
    OFFER = "offer"
    ANSWER = "answer"
    ICE = "ice"
    LEAVE = "leave"
    ERROR = "error"
    INFO = "info"
    RENEGOTIATE = "renegotiate"
    PRESENCE = "presence"
    STREAM_STATE = "stream-state"
    KICKED = "kicked"
    PAYMENT_REQUIRED = "payment-required"

    # Future extension point. Chat is already supported as a message handler.
    CHAT = "chat"


class PeerRole(str, Enum):
    PUBLISHER = "publisher"
    SUBSCRIBER = "subscriber"


class JoinMessage(BaseModel):
    type: SignalType = Field(default=SignalType.JOIN)
    token: str

    # Debug-only fields. Security decisions must use the signed token.
    roomId: Optional[str] = None
    role: Optional[PeerRole] = None
    userId: Optional[str] = None
    username: Optional[str] = None


class OfferMessage(BaseModel):
    type: SignalType = Field(default=SignalType.OFFER)
    sdp: str


class IceCandidateData(BaseModel):
    candidate: str
    sdpMid: Optional[str] = None
    sdpMLineIndex: Optional[int] = None


class IceMessage(BaseModel):
    type: SignalType = Field(default=SignalType.ICE)
    candidate: Optional[IceCandidateData] = None


class LeaveMessage(BaseModel):
    type: SignalType = Field(default=SignalType.LEAVE)


class StreamStateMessage(BaseModel):
    type: SignalType = Field(default=SignalType.STREAM_STATE)
    state: str


class ChatMessage(BaseModel):
    type: SignalType = Field(default=SignalType.CHAT)
    message: str


class KickUserRequest(BaseModel):
    stream_id: str
    user_id: str
    reason: str = "blocked"


class UnblockUserRequest(BaseModel):
    stream_id: str
    user_id: str


class EarningsUpdateRequest(BaseModel):
    stream_id: str
    earnings_summary: dict[str, Any]


SIGNAL_PARSERS = {
    SignalType.JOIN.value: JoinMessage,
    SignalType.OFFER.value: OfferMessage,
    SignalType.ICE.value: IceMessage,
    SignalType.LEAVE.value: LeaveMessage,
    SignalType.STREAM_STATE.value: StreamStateMessage,
    SignalType.CHAT.value: ChatMessage,
}


def parse_signal_message(data: dict[str, Any]):
    msg_type = data.get("type")
    parser = SIGNAL_PARSERS.get(msg_type)

    if not parser:
        raise ValueError(f"Unknown signaling message type: {msg_type}")

    return parser(**data)
