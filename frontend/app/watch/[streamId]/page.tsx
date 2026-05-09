"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { RequireAuth } from "../../../components/require-auth";
import { useSession } from "../../../components/session-provider";
import { isLiveStatus } from "../../../lib/stream-utils";
import { useSfuViewer } from "../../../lib/use-sfu-viewer";
import { useStreamRoom } from "../../../lib/use-stream-room";

export default function WatchPage() {
  return (
    <RequireAuth>
      <WatchContent />
    </RequireAuth>
  );
}

function WatchContent() {
  const params = useParams<{ streamId: string }>();
  const streamId = params.streamId;

  const router = useRouter();
  const { token, user } = useSession();

  const videoRef = useRef<HTMLVideoElement | null>(null);

  const room = useStreamRoom(streamId, token);

  const stream = room.stream;
  const isLive = isLiveStatus(stream?.status);
  const isOwner = Boolean(stream && user && stream.broadcaster_id === user.id);

  const viewer = useSfuViewer({
    token,
    streamId,
    videoRef,
    enabled: Boolean(token && stream && user && isLive && !isOwner),
  });

  const viewerCount = isLive ? viewer.viewerCount : room.apiViewerCount;
  const error = room.error || viewer.error;
  const status = isLive ? viewer.status : "This stream is not live right now.";

  useEffect(() => {
    if (isOwner) {
      router.replace(`/studio/${streamId}`);
    }
  }, [isOwner, router, streamId]);

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Watch</p>
          <h1>{stream?.title || "Opening stream..."}</h1>
          <p className="muted hero-copy">
            {stream?.description || "Waiting for metadata."}
          </p>
        </div>

        <div className="stat-block">
          <span>{isLive ? "Live viewers" : "Viewers"}</span>
          <strong>{viewerCount}</strong>
        </div>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      {room.isLoading ? (
        <section className="center-card">
          <p className="eyebrow">Loading</p>
          <h2>Opening stream.</h2>
        </section>
      ) : null}

      {!room.isLoading && stream ? (
        <div className="panel stack-md">
          <div className="video-frame">
            <video autoPlay controls playsInline ref={videoRef} />

            {viewer.isPaused ? (
              <div className="pause-overlay">
                <strong>Stream paused</strong>
              </div>
            ) : null}

            {!isLive ? (
              <div className="pause-overlay">
                <strong>Stream is not live</strong>
              </div>
            ) : null}
          </div>

          <div className="status-bar">
            <span className="status-dot" />
            <span>{status}</span>
          </div>
        </div>
      ) : null}

      {isLive ? (
        <div className="panel stack-md">
          <div>
            <p className="eyebrow">Live viewers</p>
            <h2>{viewerCount} watching</h2>
          </div>

          {viewer.viewers.length === 0 ? (
            <p className="muted">No viewers connected yet.</p>
          ) : (
            <ul className="viewer-list">
              {viewer.viewers.map((liveViewer) => (
                <li key={liveViewer.peerId}>
                  <strong>{liveViewer.username}</strong>
                  <span>{liveViewer.userId}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </section>
  );
}