from aiortc.contrib.media import MediaRelay


class MediaRouter:
    def __init__(self):
        self.relay = MediaRelay()

    async def handle_publisher_track(self, room, track):
        kind = track.kind
        room.add_track(kind, track)

        print(f"[MediaRouter] Publisher track received: {kind}")

        for subscriber in room.get_subscribers():
            await self.attach_track_to_subscriber(room, subscriber, kind)
            await subscriber.send_json(
                {
                    "type": "renegotiate",
                    "reason": f"new {kind} track available",
                }
            )

    async def attach_existing_tracks_to_subscriber(self, room, subscriber):
        for published_track in room.get_all_tracks():
            await self.attach_track_to_subscriber(
                room=room,
                subscriber=subscriber,
                kind=published_track.kind,
            )

    async def attach_track_to_subscriber(self, room, subscriber, kind: str):
        if not subscriber.pc:
            return

        if kind in subscriber.attached_kinds:
            return

        source_track = room.get_track(kind)

        if source_track is None:
            return

        relayed_track = self.relay.subscribe(source_track)
        subscriber.pc.addTrack(relayed_track)
        subscriber.attached_kinds.add(kind)

        print(
            f"[MediaRouter] Attached {kind} track "
            f"to subscriber {subscriber.id}"
        )