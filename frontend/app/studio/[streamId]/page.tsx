"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { RequireAuth } from "../../../components/require-auth";
import { useSession } from "../../../components/session-provider";
import { api, WS_BASE_URL } from "../../../lib/api";
import type { StreamDetailsResponse, StreamRecord } from "../../../lib/types";

type SignalMessage = {
  type: string;
  from: string;
  to?: string;
  data?: RTCSessionDescriptionInit | RTCIceCandidateInit | { userId?: string };
};

export default function StudioRoomPage() {
  return (
    <RequireAuth>
      <StudioRoomContent />
    </RequireAuth>
  );
}

function StudioRoomContent() {
  const params = useParams<{ streamId: string }>();
  const { token, user } = useSession();
  const streamId = params.streamId;
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const peersRef = useRef<Map<string, RTCPeerConnection>>(new Map());
  const [stream, setStream] = useState<StreamRecord | null>(null);
  const [viewerCount, setViewerCount] = useState(0);
  const [status, setStatus] = useState("Loading room...");
  const [error, setError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  const isOwner = stream?.broadcaster_id === user?.id;

  useEffect(() => {
    const loadRoom = async () => {
      try {
        const response = await api.getStream(streamId);
        setStream(response.stream);
        setViewerCount(response.viewer_count);
        setStatus(
          response.stream.status === "live"
            ? "Stream is live. Enable camera to start serving viewers."
            : "Stream is offline. Start it when you are ready."
        );
      } catch (roomError) {
        const message = roomError instanceof Error ? roomError.message : "Failed to load stream";
        setError(message);
      }
    };

    void loadRoom();
  }, [streamId]);

  useEffect(() => {
    if (videoRef.current && mediaRef.current) {
      videoRef.current.srcObject = mediaRef.current;
    }
  }, [cameraReady]);

  useEffect(() => {
    if (!token || !stream || stream.status !== "live" || !cameraReady || !isOwner) {
      return;
    }

    let cancelled = false;

    const connectRoom = async () => {
      try {
        const ticket = await api.getWsTicket(token, streamId);
        if (cancelled) {
          return;
        }

        const socket = new WebSocket(`${WS_BASE_URL}/ws/stream/${streamId}?ticket=${ticket.ticket}`);
        socketRef.current = socket;

        socket.onopen = () => {
          setStatus("Broadcast room connected. Waiting for viewers.");
        };

        socket.onmessage = async (event) => {
          const message = JSON.parse(event.data) as SignalMessage;

          if (message.type === "viewer-ready" && message.from) {
            setStatus("Viewer joined. Negotiating media...");
            await createAndSendOffer(message.from);
          }

          if (message.type === "answer" && message.from) {
            const peer = peersRef.current.get(message.from);
            const answer = message.data as RTCSessionDescriptionInit | undefined;
            if (peer && answer) {
              await peer.setRemoteDescription(new RTCSessionDescription(answer));
              setStatus("Viewer connected.");
            }
          }

          if (message.type === "ice" && message.from) {
            const peer = peersRef.current.get(message.from);
            const candidate = message.data as RTCIceCandidateInit | undefined;
            if (peer && candidate) {
              await peer.addIceCandidate(new RTCIceCandidate(candidate));
            }
          }
        };

        socket.onerror = () => {
          setError("Broadcast websocket disconnected unexpectedly.");
        };

        socket.onclose = () => {
          socketRef.current = null;
        };
      } catch (connectError) {
        const message =
          connectError instanceof Error ? connectError.message : "Failed to connect broadcast room";
        setError(message);
      }
    };

    void connectRoom();

    return () => {
      cancelled = true;
      socketRef.current?.close();
      socketRef.current = null;
      for (const peer of peersRef.current.values()) {
        peer.close();
      }
      peersRef.current.clear();
    };
  }, [cameraReady, isOwner, stream, streamId, token]);

  const ensurePeer = (viewerId: string) => {
    const existing = peersRef.current.get(viewerId);
    if (existing) {
      return existing;
    }

    const peer = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

    mediaRef.current?.getTracks().forEach((track) => {
      if (mediaRef.current) {
        peer.addTrack(track, mediaRef.current);
      }
    });

    peer.onicecandidate = (event) => {
      if (event.candidate && socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({
            type: "ice",
            to: viewerId,
            data: event.candidate.toJSON(),
          })
        );
      }
    };

    peer.onconnectionstatechange = () => {
      if (peer.connectionState === "failed" || peer.connectionState === "closed") {
        peer.close();
        peersRef.current.delete(viewerId);
      }
    };

    peersRef.current.set(viewerId, peer);
    return peer;
  };

  const createAndSendOffer = async (viewerId: string) => {
    const peer = ensurePeer(viewerId);
    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);

    socketRef.current?.send(
      JSON.stringify({
        type: "offer",
        to: viewerId,
        data: offer,
      })
    );
  };

  const enableCamera = async () => {
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });
      mediaRef.current = media;
      setCameraReady(true);
      if (videoRef.current) {
        videoRef.current.srcObject = media;
      }
      setStatus("Camera ready.");
    } catch (mediaError) {
      const message = mediaError instanceof Error ? mediaError.message : "Camera access failed";
      setError(message);
    }
  };

  const handleStart = async () => {
    if (!token) {
      return;
    }

    setIsStarting(true);
    setError(null);

    try {
      const updated = await api.startStream(token, streamId);
      setStream(updated);
      setStatus("Stream is now live. Enable camera to begin sending video.");
    } catch (startError) {
      const message = startError instanceof Error ? startError.message : "Failed to start stream";
      setError(message);
    } finally {
      setIsStarting(false);
    }
  };

  const handleEnd = async () => {
    if (!token) {
      return;
    }

    setIsEnding(true);
    setError(null);

    try {
      const updated = await api.endStream(token, streamId);
      setStream(updated);
      socketRef.current?.close();
      mediaRef.current?.getTracks().forEach((track) => track.stop());
      mediaRef.current = null;
      setCameraReady(false);
      for (const peer of peersRef.current.values()) {
        peer.close();
      }
      peersRef.current.clear();
      setStatus("Stream ended.");
    } catch (endError) {
      const message = endError instanceof Error ? endError.message : "Failed to end stream";
      setError(message);
    } finally {
      setIsEnding(false);
    }
  };

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Studio room</p>
          <h1>{stream?.title || "Opening stream room..."}</h1>
          <p className="muted hero-copy">{stream?.description || "No description available."}</p>
        </div>
        <div className="stat-block">
          <span>Active viewers</span>
          <strong>{viewerCount}</strong>
        </div>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      {!stream ? (
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
          <div className="panel stack-md">
            <div className="video-frame">
              <video autoPlay muted playsInline ref={videoRef} />
            </div>
            <div className="status-bar">
              <span className="status-dot" />
              <span>{status}</span>
            </div>
          </div>

          <div className="panel stack-md">
            <div>
              <p className="eyebrow">Broadcast controls</p>
              <h2>Manage this live room</h2>
            </div>
            <div className="stack-sm">
              <button className="primary-button" onClick={enableCamera} type="button">
                {cameraReady ? "Camera ready" : "Enable camera"}
              </button>
              <button
                className="ghost-button"
                disabled={stream.status === "live" || isStarting}
                onClick={handleStart}
                type="button"
              >
                {isStarting ? "Starting..." : "Start stream"}
              </button>
              <button
                className="ghost-button danger"
                disabled={stream.status !== "live" || isEnding}
                onClick={handleEnd}
                type="button"
              >
                {isEnding ? "Ending..." : "End stream"}
              </button>
            </div>
            <div className="meta-list">
              <div>
                <span>Status</span>
                <strong>{stream.status}</strong>
              </div>
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
