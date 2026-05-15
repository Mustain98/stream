from typing import Dict


class PublishedTrack:
    def __init__(self, kind: str, track):
        self.kind = kind
        self.track = track


class Room:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.publisher = None
        self.subscribers: Dict[str, object] = {}
        self.tracks: Dict[str, PublishedTrack] = {}
        self.stream_state = "live"
        self.blocked_user_ids: set[str] = set()

    def set_publisher(self, peer):
        self.publisher = peer

    def add_subscriber(self, peer):
        self.subscribers[peer.id] = peer

    def remove_peer(self, peer_id: str):
        if self.publisher and self.publisher.id == peer_id:
            print(f"[Room {self.room_id}] Publisher removed")
            self.publisher = None
            self.tracks.clear()
            self.stream_state = "live"

        if peer_id in self.subscribers:
            print(f"[Room {self.room_id}] Subscriber removed:", peer_id)
            del self.subscribers[peer_id]

    def add_track(self, kind: str, track):
        print(f"[Room {self.room_id}] Added publisher track:", kind)
        self.tracks[kind] = PublishedTrack(kind=kind, track=track)

    def get_track(self, kind: str):
        published = self.tracks.get(kind)
        return published.track if published else None

    def get_all_tracks(self):
        return list(self.tracks.values())

    def get_subscribers(self):
        return list(self.subscribers.values())

    def get_all_peers(self):
        peers = []

        if self.publisher:
            peers.append(self.publisher)

        peers.extend(self.subscribers.values())
        return peers

    def is_empty(self):
        return self.publisher is None and len(self.subscribers) == 0

    def block_user(self, user_id: str):
        self.blocked_user_ids.add(str(user_id))

    def unblock_user(self, user_id: str):
        self.blocked_user_ids.discard(str(user_id))

    def is_user_blocked(self, user_id: str | None):
        if user_id is None:
            return False

        return str(user_id) in self.blocked_user_ids

    def find_subscribers_by_user_id(self, user_id: str):
        return [
            peer
            for peer in self.subscribers.values()
            if str(peer.user_id) == str(user_id)
        ]

    def get_viewer_list(self):
        return [
            {
                "peerId": peer.id,
                "userId": peer.user_id,
                "username": peer.username,
            }
            for peer in self.subscribers.values()
        ]

    def get_presence_payload(self):
        viewers = self.get_viewer_list()

        return {
            "type": "presence",
            "roomId": self.room_id,
            "viewerCount": len(viewers),
            "viewers": viewers,
        }

    async def broadcast(self, payload: dict, include_publisher: bool = True):
        targets = self.get_all_peers() if include_publisher else self.get_subscribers()

        for peer in targets:
            try:
                await peer.send_json(payload)
            except Exception as exc:
                print(f"[Room {self.room_id}] Failed to broadcast:", str(exc))

    async def broadcast_presence(self):
        await self.broadcast(self.get_presence_payload())

    async def broadcast_stream_state(self):
        await self.broadcast(
            {
                "type": "stream-state",
                "roomId": self.room_id,
                "state": self.stream_state,
            }
        )

    async def kick_user(self, user_id: str, reason: str = "blocked") -> int:
        targets = self.find_subscribers_by_user_id(user_id)

        for peer in targets:
            try:
                await peer.send_json(
                    {
                        "type": "kicked",
                        "reason": reason,
                        "message": "You were removed from this live stream.",
                    }
                )
            except Exception as exc:
                print(f"[Room {self.room_id}] Failed to notify kicked peer:", exc)

            await peer.close(close_websocket=True)
            self.remove_peer(peer.id)

        if targets:
            await self.broadcast_presence()

        return len(targets)
    
    def find_peer_by_username(self, username: str):
        target = username.lower()

        if self.publisher and self.publisher.username.lower() == target:
            return self.publisher

        for peer in self.subscribers.values():
            if peer.username.lower() == target:
                return peer

        return None

    def find_peers_by_usernames(self, usernames: list[str]):
        peers = []

        seen_user_ids = set()

        for username in usernames:
            peer = self.find_peer_by_username(username)

            if not peer:
                continue

            if peer.user_id in seen_user_ids:
                continue

            seen_user_ids.add(peer.user_id)
            peers.append(peer)

        return peers
