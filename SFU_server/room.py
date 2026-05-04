from typing import Optional,Dict

class PublishedTrack:
    def __init__(self,kind:str,track):
        self.kind=kind
        self.track=track

class Room:
    def __init__(self,room_id:str):
        self.room_id=room_id

        self.publisher =None
        self.subscribers: Dict[str, object] = {}

        self.tracks: Dict[str,PublishedTrack]={}

    def set_publisher(self,peer):
        self.publisher=peer
    
    def add_subscriber(self,peer):
        self.subscribers[peer.id]=peer

    def remove_peer(self,peer_id):
        if self.publisher and self.publisher.id == peer_id:
            print(f"[Room {self.room_id}] Publisher removed")
            self.publisher = None
            self.tracks.clear()

        if peer_id in self.subscribers:
            print(f"[Room {self.room_id}] Subscriber removed:", peer_id)
            del self.subscribers[peer_id]

    def add_track(self, kind: str, track):
            print(f"[Room {self.room_id}] Added publisher track:", kind)
            self.tracks[kind] = PublishedTrack(kind=kind, track=track)

    def get_track(self, kind: str):
        published = self.tracks.get(kind)
        if published:
            return published.track
        return None

    def get_all_tracks(self):
        return list(self.tracks.values())

    def get_subscribers(self):
        return list(self.subscribers.values())

    def is_empty(self):
        return self.publisher is None and len(self.subscribers) == 0
