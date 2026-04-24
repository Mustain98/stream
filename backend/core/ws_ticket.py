import uuid
from datetime import datetime, timedelta


TICKET_TTL = 120  # seconds

WS_TICKETS = {}

def create_ws_ticket(user_id: str, stream_id: str, role: str):
    ticket = str(uuid.uuid4())

    WS_TICKETS[ticket] = {
        "user_id": user_id,
        "stream_id": stream_id,
        "role": role,
        "expires": datetime.utcnow() + timedelta(seconds=TICKET_TTL)
    }

    return ticket


def verify_ws_ticket(ticket: str):
    data = WS_TICKETS.get(ticket)

    if not data:
        return None

    if data["expires"] < datetime.utcnow():
        WS_TICKETS.pop(ticket, None)
        return None

    return data


def consume_ws_ticket(ticket: str):
    return WS_TICKETS.pop(ticket, None)