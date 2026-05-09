"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { RequireAuth } from "../../../components/require-auth";
import { StudioControlsPanel } from "../../../components/studio-control-panel";
import { StudioVideoPanel } from "../../../components/studio-video-panel";
import { useSession } from "../../../components/session-provider";
import { api } from "../../../lib/api";
import { isEndedStatus, isLiveStatus } from "../../../lib/stream-utils";
import { useSfuPublisher } from "../../../lib/use-sfu-publisher";
import { useStreamModeration } from "../../../lib/use-stream-moderation";
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
  const publisher = useSfuPublisher({ token, streamId });

  const moderation = useStreamModeration({
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

  const error =
    localError || room.error || publisher.error || moderation.moderationError;

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
    if (!stream || !isOwner || !token) {
      return;
    }

    void moderation.loadBlockedUsers();
  }, [stream?.id, isOwner, token, moderation.loadBlockedUsers]);

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

    // Intentionally limited to avoid reconnect loops.
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
          <StudioVideoPanel
            videoRef={videoRef}
            isLive={isLive}
            isEnded={isEnded}
            cameraReady={cameraReady}
            isPaused={publisher.isPaused}
            isConnected={publisher.isConnected}
            isCameraEnabled={publisher.isCameraEnabled}
            isMicEnabled={publisher.isMicEnabled}
            status={status}
            reconnectFailed={publisher.reconnectFailed}
            viewerCount={viewerCount}
            viewers={viewers}
            onTogglePause={publisher.togglePause}
            onToggleCamera={publisher.toggleCamera}
            onToggleMic={publisher.toggleMic}
            onBlockViewer={moderation.blockViewer}
          />

          <StudioControlsPanel
            stream={stream}
            isLive={isLive}
            isEnded={isEnded}
            canGoLive={canGoLive}
            isUpdatingStream={isUpdatingStream}
            publisherIsConnecting={publisher.isConnecting}
            publisherIsConnected={publisher.isConnected}
            publisherIsReconnecting={publisher.isReconnecting}
            publisherReconnectFailed={publisher.reconnectFailed}
            publisherIsPaused={publisher.isPaused}
            publisherIsCameraEnabled={publisher.isCameraEnabled}
            publisherIsMicEnabled={publisher.isMicEnabled}
            viewerCount={viewerCount}
            blockedUsers={moderation.blockedUsers}
            isLoadingBlockedUsers={moderation.isLoadingBlockedUsers}
            onGoLive={goLive}
            onEndLive={endLive}
            onTryAgain={tryAgain}
            onUnblockViewer={moderation.unblockViewer}
          />
        </div>
      ) : null}
    </section>
  );
}