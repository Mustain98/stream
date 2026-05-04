from enum import Enum
from typing import Optional, Any
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


class PeerRole(str, Enum):
    PUBLISHER = "publisher"
    SUBSCRIBER = "subscriber"


class JoinMessage(BaseModel):
    type: SignalType = Field(default=SignalType.JOIN)
    roomId: str
    role: PeerRole

    # Sent by frontend for now.
    # Later, get these by verifying the SFU ticket.
    token: Optional[str] = None
    userId: Optional[str] = None
    username: Optional[str] = None


class OfferMessage(BaseModel):
    type: SignalType = Field(default=SignalType.OFFER)
    sdp: str


class AnswerMessage(BaseModel):
    type: SignalType = Field(default=SignalType.ANSWER)
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


class ErrorMessage(BaseModel):
    type: SignalType = Field(default=SignalType.ERROR)
    message: str


class PresenceViewer(BaseModel):
    peerId: str
    userId: Optional[str] = None
    username: str


class PresenceMessage(BaseModel):
    type: SignalType = Field(default=SignalType.PRESENCE)
    roomId: str
    viewerCount: int
    viewers: list[PresenceViewer]


def parse_signal_message(data: dict[str, Any]):
    msg_type = data.get("type")

    if msg_type == SignalType.JOIN.value:
        return JoinMessage(**data)

    if msg_type == SignalType.OFFER.value:
        return OfferMessage(**data)

    if msg_type == SignalType.ICE.value:
        return IceMessage(**data)

    if msg_type == SignalType.LEAVE.value:
        return LeaveMessage(**data)

    raise ValueError(f"Unknown signaling message type: {msg_type}")