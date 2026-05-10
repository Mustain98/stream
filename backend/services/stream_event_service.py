from sqlmodel import Session

from models import StreamEvent, EventType


def create_stream_event(
    session: Session,
    stream_id: str,
    event_type: EventType,
    user_id: str | None = None,
    message: str | None = None,
) -> StreamEvent:
    event = StreamEvent(
        stream_id=stream_id,
        user_id=user_id,
        event_type=event_type,
        message=message,
    )

    session.add(event)

    return event