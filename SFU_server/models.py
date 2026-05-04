from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class SignalType(str,Enum):
    JOIN="join"
    OFFER="offer"
    ANSWER="answer"
    ICE="ice"
    LEAVE="leave"
    ERROR="error"
    PRESENCE = "presence"

class PeerRole(str,Enum):
    PUBLISHER="publisher"
    SUBSCRIBER="subscriber"

class JoinMessage(BaseModel):
    type:SignalType=Field(default=SignalType.JOIN)
    roomId:str
    role:PeerRole

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


def parse_signal_message(data: dict):
    """
    Converts raw websocket JSON data into the correct Pydantic model.

    Example:
        msg = parse_signal_message(data)

        if msg.type == SignalType.JOIN:
            ...
    """

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