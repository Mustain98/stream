"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { RequireAuth } from "../../../components/require-auth";
import { useSession } from "../../../components/session-provider";
import { api } from "../../../lib/api";
import { isEndedStatus, isLiveStatus } from "../../../lib/stream-utils";
import { useSfuPublisher } from "../../../lib/use-sfu-publisher";
import { useStreamRoom } from "../../../lib/use-stream-room";

export default function StudioRoomPage() {
  return (
    <RequireAuth>
      <StudioRoomContent />
    </RequireAuth>
  );
}

function StudioRoomContent() {
  const params = useParams<{ streamId: string }>();
  const streamId = params.streamId;

  const { token, user } = useSession();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);

  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [isUpdatingStream, setIsUpdatingStream] = useState(false);
  const [localStatus, setLocalStatus] = useState("Loading room...");
  const [localError, setLocalError] = useState<string | null>(null);

  const room = useStreamRoom(streamId, token);

  const publisher = useSfuPublisher({
    token,
    streamId,
  });

  const stream = room.stream;
  const isOwner = stream?.broadcaster_id === user?.id;

  const isLive = isLiveStatus(stream?.status);
  const isEnded = isEndedStatus(stream?.status);
  const canGoLive = Boolean(stream && !isLive && !isEnded);

  const cameraReady = Boolean(localStream);

  const viewerCount = isLive ? publisher.viewerCount : room.apiViewerCount;
  const viewers = isLive ? publisher.viewers : [];

  const error = localError || room.error || publisher.error;

  const status = useMemo(() => {
    if (isEnded) {
      return "This stream has ended.";
    }

    if (publisher.isReconnecting) {
      return "Reconnecting broadcast...";
    }

    if (publisher.reconnectFailed) {
      return "Could not reconnect.";
    }

    if (publisher.isConnecting) {
      return "Connecting broadcast...";
    }

    if (publisher.isConnected || publisher.status !== "Not connected.") {
      return publisher.status;
    }

    if (stream) {
      if (isLive) {
        return "Stream is live. Restoring broadcast if possible.";
      }

      return "Stream is ready. Click Go Live when you are ready.";
    }

    return localStatus;
  }, [
    isEnded,
    publisher.isReconnecting,
    publisher.reconnectFailed,
    publisher.isConnecting,
    publisher.isConnected,
    publisher.status,
    stream,
    isLive,
    localStatus,
  ]);

  useEffect(() => {
    if (videoRef.current && localStream) {
      videoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  useEffect(() => {
    publisher.setMediaStream(localStream);
  }, [localStream, publisher.setMediaStream]);

  useEffect(() => {
    return () => {
      publisher.cleanup();
    };
  }, [publisher.cleanup]);

  useEffect(() => {
    return () => {
      localStreamRef.current?.getTracks().forEach((track) => {
        track.stop();
      });

      localStreamRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!stream || !isOwner || !isLive || isEnded) {
      return;
    }

    if (publisher.isConnected || publisher.isConnecting || publisher.isReconnecting) {
      return;
    }

    if (publisher.reconnectFailed) {
      return;
    }

    const restoreBroadcast = async () => {
      const media = await ensureMedia();

      if (!media) {
        return;
      }

      await publisher.connect({
        mediaStream: media,
        isPaused: publisher.isPaused,
        isMicEnabled: publisher.isMicEnabled,
        isCameraEnabled: publisher.isCameraEnabled,
      });
    };

    void restoreBroadcast();

    // Intentionally limited dependencies to avoid reconnect loops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream?.id, isOwner, isLive, isEnded]);

  const ensureMedia = async () => {
    if (localStreamRef.current) {
      return localStreamRef.current;
    }

    try {
      setLocalError(null);

      const media = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });

      localStreamRef.current = media;
      setLocalStream(media);
      publisher.setMediaStream(media);

      if (videoRef.current) {
        videoRef.current.srcObject = media;
      }

      setLocalStatus("Camera ready.");

      return media;
    } catch (mediaError) {
      const message =
        mediaError instanceof Error ? mediaError.message : "Camera access failed";

      setLocalError(message);
      return null;
    }
  };

  const stopMedia = () => {
    localStreamRef.current?.getTracks().forEach((track) => {
      track.stop();
    });

    localStreamRef.current = null;
    setLocalStream(null);
    publisher.setMediaStream(null);

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  const goLive = async () => {
    if (!token || !stream || !canGoLive) {
      return;
    }

    setIsUpdatingStream(true);
    setLocalError(null);

    try {
      const media = await ensureMedia();

      if (!media) {
        return;
      }

      const updated = await api.startStream(token, streamId);
      room.setStream(updated);

      await publisher.connect({
        mediaStream: media,
        isPaused: publisher.isPaused,
        isMicEnabled: publisher.isMicEnabled,
        isCameraEnabled: publisher.isCameraEnabled,
      });

      setLocalStatus("Broadcasting.");
    } catch (goLiveError) {
      const message =
        goLiveError instanceof Error ? goLiveError.message : "Failed to go live";

      setLocalError(message);
    } finally {
      setIsUpdatingStream(false);
    }
  };

  const endLive = async () => {
    if (!token || !stream || !isLive) {
      return;
    }

    setIsUpdatingStream(true);
    setLocalError(null);

    try {
      const updated = await api.endStream(token, streamId);

      publisher.cleanup();
      stopMedia();

      room.setStream(updated);
      await room.loadApiViewerCount();

      setLocalStatus("Stream ended.");
    } catch (endError) {
      const message =
        endError instanceof Error ? endError.message : "Failed to end stream";

      setLocalError(message);
    } finally {
      setIsUpdatingStream(false);
    }
  };

  const tryAgain = async () => {
    if (!isLive || isEnded) {
      return;
    }

    const media = await ensureMedia();

    if (!media) {
      return;
    }

    await publisher.connect({
      mediaStream: media,
      isPaused: publisher.isPaused,
      isMicEnabled: publisher.isMicEnabled,
      isCameraEnabled: publisher.isCameraEnabled,
    });
  };

  const formatDateTime = (value: string | null) => {
    if (!value) {
      return "—";
    }

    return new Date(value).toLocaleString();
  };

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Studio room</p>
          <h1>{stream?.title || "Opening stream room..."}</h1>
          <p className="muted hero-copy">
            {stream?.description || "No description available."}
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
          <h2>Pulling stream details.</h2>
        </section>
      ) : null}

      {stream && !isOwner ? (
        <section className="center-card error-surface">
          <p className="eyebrow">Access denied</p>
          <h2>This stream belongs to another broadcaster.</h2>

          <Link className="primary-button compact" href={`/watch/${streamId}`}>
            Open watch page instead
          </Link>
        </section>
      ) : null}

  {stream && isOwner ? (
    <div className="studio-room-grid">
      {/* LEFT PANEL */}
      <div className="panel stack-md">
        <div className="video-frame">
          <video autoPlay muted playsInline ref={videoRef} />

          {publisher.isPaused && isLive ? (
            <div className="pause-overlay">
              <strong>Paused</strong>
            </div>
          ) : null}

          {isEnded ? (
            <div className="pause-overlay">
              <strong>Stream ended</strong>
            </div>
          ) : null}
        </div>

        {isLive && !isEnded ? (
          <div className="video-resource-controls">
            <button
              aria-label={publisher.isPaused ? "Resume stream" : "Pause stream"}
              className={publisher.isPaused ? "resource-button active" : "resource-button"}
              disabled={!cameraReady || !publisher.isConnected}
              onClick={publisher.togglePause}
              title={publisher.isPaused ? "Resume stream" : "Pause stream"}
              type="button"
            >
              {publisher.isPaused ? "▶" : "⏸"}
            </button>

            <button
              aria-label={publisher.isCameraEnabled ? "Turn camera off" : "Turn camera on"}
              className={
                publisher.isCameraEnabled ? "resource-button" : "resource-button muted"
              }
              disabled={!cameraReady || publisher.isPaused}
              onClick={publisher.toggleCamera}
              title={publisher.isCameraEnabled ? "Turn camera off" : "Turn camera on"}
              type="button"
            >
              {publisher.isCameraEnabled ? "🎥" : "🚫"}
            </button>

            <button
              aria-label={publisher.isMicEnabled ? "Mute mic" : "Unmute mic"}
              className={publisher.isMicEnabled ? "resource-button" : "resource-button muted"}
              disabled={!cameraReady || publisher.isPaused}
              onClick={publisher.toggleMic}
              title={publisher.isMicEnabled ? "Mute mic" : "Unmute mic"}
              type="button"
            >
              {publisher.isMicEnabled ? "🎙" : "🔇"}
            </button>
          </div>
        ) : null}

        <div className="status-bar">
          <span className="status-dot" />
          <span>{status}</span>
        </div>

        {publisher.reconnectFailed && isLive && !isEnded ? (
          <div className="error-banner">
            <strong>Connection lost.</strong>{" "}
            Your stream may still be live for a short time.
          </div>
        ) : null}

        <div className="panel stack-md">
          <div>
            <p className="eyebrow">{isLive ? "Live viewers" : "Viewers"}</p>
            <h2>
              {viewerCount} {isLive ? "watching" : "viewers"}
            </h2>
          </div>

          {isLive ? (
            viewers.length === 0 ? (
              <p className="muted">No viewers connected yet.</p>
            ) : (
              <ul className="viewer-list">
                {viewers.map((viewer) => (
                  <li key={viewer.peerId}>
                    <strong>{viewer.username}</strong>
                    <span>{viewer.userId}</span>
                  </li>
                ))}
              </ul>
            )
          ) : (
            <p className="muted">
              This viewer count is loaded from the saved stream record.
            </p>
          )}
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div className="panel stack-md">
        <div>
          <p className="eyebrow">Broadcast controls</p>
          <h2>{isEnded ? "Stream summary" : "Manage this room"}</h2>
        </div>

        <div className="stack-sm">
          {canGoLive ? (
            <button
              className="primary-button"
              disabled={isUpdatingStream || publisher.isConnecting}
              onClick={goLive}
              type="button"
            >
              {isUpdatingStream || publisher.isConnecting ? "Going live..." : "Go Live"}
            </button>
          ) : null}

          {isLive ? (
            <button
              className="ghost-button danger"
              disabled={isUpdatingStream}
              onClick={endLive}
              type="button"
            >
              {isUpdatingStream ? "Ending..." : "End Live"}
            </button>
          ) : null}

          {isEnded ? (
            <Link className="primary-button" href="/studio">
              Back to studio
            </Link>
          ) : null}

          {publisher.reconnectFailed && isLive && !isEnded ? (
            <button className="primary-button" onClick={tryAgain} type="button">
              Try Again
            </button>
          ) : null}
        </div>

        <div className="meta-list">
          <div>
            <span>Status</span>
            <strong>{stream.status}</strong>
          </div>

          {isEnded ? (
            <>
              <div>
                <span>Viewers</span>
                <strong>{viewerCount}</strong>
              </div>

              <div>
                <span>Started</span>
                <strong>{formatDateTime(stream.started_at)}</strong>
              </div>

              <div>
                <span>Ended</span>
                <strong>{formatDateTime(stream.ended_at)}</strong>
              </div>
            </>
          ) : (
            <>
              <div>
                <span>Broadcast</span>
                <strong>
                  {publisher.isConnected
                    ? "connected"
                    : publisher.isReconnecting
                      ? "reconnecting"
                      : "not connected"}
                </strong>
              </div>

              <div>
                <span>Camera</span>
                <strong>{publisher.isCameraEnabled ? "on" : "off"}</strong>
              </div>

              <div>
                <span>Mic</span>
                <strong>{publisher.isMicEnabled ? "on" : "muted"}</strong>
              </div>

              <div>
                <span>Playback</span>
                <strong>{publisher.isPaused ? "paused" : "live"}</strong>
              </div>
            </>
          )}

          <div>
            <span>Stream ID</span>
            <strong>{stream.id}</strong>
          </div>
        </div>
      </div>
    </div>
  ) : null}
    </section>
  );
}