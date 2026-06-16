from sfu.room import Room

rooms: dict[str, Room] = {}


def get_or_create_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room(room_id)
        print(f"[State] Created room: {room_id}")

    return rooms[room_id]


def remove_room_if_empty(room_id: str) -> None:
    room = rooms.get(room_id)

    if room and room.is_empty():
        del rooms[room_id]
        print(f"[State] Removed empty room: {room_id}")
