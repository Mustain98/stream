"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { RequireAuth } from "../../../components/require-auth";
import { useSession } from "../../../components/session-provider";
import { api, WS_BASE_URL } from "../../../lib/api";
import type { StreamRecord } from "../../../lib/types";

type SignalMessage = {
  type: string;
  from: string;
  to?: string;
  data?: RTCSessionDescriptionInit | RTCIceCandidateInit;
};

export default function WatchPage() {
  return (
    <RequireAuth>
      <WatchContent />
    </RequireAuth>
  );
}

function WatchContent() {
  const params = useParams<{ streamId: string }>();
  const router = useRouter();
  const streamId = params.streamId;
  const { token, user } = useSession();
  const [stream, setStream] = useState<StreamRecord | null>(null);
  const [viewerCount, setViewerCount] = useState(0);
  const [status, setStatus] = useState("Loading stream...");
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const isConnectingRef = useRef(false);
  const joinedRef = useRef(false);
  const tokenRef = useRef<string | null>(null);

  useEffect(() => {
    joinedRef.current = joined;
  }, [joined]);

  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  useEffect(() => {
    const loadStream = async () => {
      try {
        const response = await api.getStream(streamId);
        setStream(response.stream);
        setViewerCount(response.viewer_count);
        setStatus(
          response.stream.status === "live"
            ? "Preparing to join the live room."
            : "This stream is not live right now."
        );
      } catch (streamError) {
        const message = streamError instanceof Error ? streamError.message : "Failed to load";
        setError(message);
      }
    };

    void loadStream();
  }, [streamId]);

  useEffect(() => {
    if (!stream || !user) {
      return;
    }

    if (stream.broadcaster_id === user.id) {
      router.replace(`/studio/${streamId}`);
    }
  }, [router, stream, streamId, user]);

  useEffect(() => {
    if (!token || !stream || stream.status !== "live" || joined) {
      return;
    }

    if (stream.broadcaster_id === user?.id) {
      return;
    }

    if (isConnectingRef.current) {
      return;
    }

    let cancelled = false;
    isConnectingRef.current = true;

    const connectViewer = async () => {
      try {
        await api.joinStream(token, streamId);
        if (cancelled) {
          isConnectingRef.current = false;
          return;
        }

        setStatus("Joined the room. Waiting for the broadcaster.");

        const ticket = await api.getWsTicket(token, streamId);
        if (cancelled) {
          isConnectingRef.current = false;
          return;
        }

        const socket = new WebSocket(`${WS_BASE_URL}/ws/stream/${streamId}?ticket=${ticket.ticket}`);
        socketRef.current = socket;

        socket.onopen = () => {
          setJoined(true);
          socket.send(JSON.stringify({ type: "viewer-ready", data: { userId: user?.id } }));
        };

        socket.onmessage = async (event) => {
          const message = JSON.parse(event.data) as SignalMessage;

          if (message.type === "broadcaster-ready") {
            socket.send(JSON.stringify({ type: "viewer-ready", data: { userId: user?.id } }));
            setStatus("Broadcaster is ready. Requesting live feed.");
          }

          if (message.type === "offer" && message.data) {
            const peer = createPeerConnection();
            const offer = message.data as RTCSessionDescriptionInit;
            await peer.setRemoteDescription(new RTCSessionDescription(offer));
            const answer = await peer.createAnswer();
            await peer.setLocalDescription(answer);
            socket.send(
              JSON.stringify({
                type: "answer",
                to: message.from,
                data: answer,
              })
            );
            setStatus("Receiving live video.");
          }

          if (message.type === "ice" && message.data && peerRef.current) {
            const candidate = message.data as RTCIceCandidateInit;
            await peerRef.current.addIceCandidate(new RTCIceCandidate(candidate));
          }
        };

        socket.onerror = () => {
          isConnectingRef.current = false;
          setError("Viewer websocket disconnected unexpectedly.");
        };

        socket.onclose = () => {
          isConnectingRef.current = false;
          socketRef.current = null;
        };
      } catch (joinError) {
        const message = joinError instanceof Error ? joinError.message : "Unable to join stream";
        setError(message);
        isConnectingRef.current = false;
      }
    };

    void connectViewer();

    return () => {
      cancelled = true;
      isConnectingRef.current = false;
    };
  }, [joined, stream, streamId, token, user?.id]);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      peerRef.current?.close();
      remoteStreamRef.current?.getTracks().forEach((track) => track.stop());
      if (tokenRef.current && joinedRef.current) {
        void api.leaveStream(tokenRef.current, streamId).catch(() => undefined);
      }
      isConnectingRef.current = false;
    };
  }, [streamId]);

  const createPeerConnection = () => {
    if (peerRef.current) {
      return peerRef.current;
    }

    const peer = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

    peer.addTransceiver("video", { direction: "recvonly" });
    peer.addTransceiver("audio", { direction: "recvonly" });

    peer.ontrack = (event) => {
      if (!remoteStreamRef.current) {
        remoteStreamRef.current = new MediaStream();
      }

      const existingTrackIds = new Set(
        remoteStreamRef.current.getTracks().map((track) => track.id)
      );
      if (!existingTrackIds.has(event.track.id)) {
        remoteStreamRef.current.addTrack(event.track);
      }

      if (videoRef.current && remoteStreamRef.current) {
        videoRef.current.srcObject = remoteStreamRef.current;
        void videoRef.current.play().catch(() => undefined);
      }
    };

    peer.onicecandidate = (event) => {
      if (
        event.candidate &&
        socketRef.current?.readyState === WebSocket.OPEN &&
        stream?.broadcaster_id
      ) {
        socketRef.current.send(
          JSON.stringify({
            type: "ice",
            to: stream.broadcaster_id,
            data: event.candidate.toJSON(),
          })
        );
      }
    };

    peerRef.current = peer;
    return peer;
  };

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Watch live</p>
          <h1>{stream?.title || "Opening stream..."}</h1>
          <p className="muted hero-copy">{stream?.description || "Waiting for metadata."}</p>
        </div>
        <div className="stat-block">
          <span>Viewers</span>
          <strong>{viewerCount}</strong>
        </div>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      <div className="panel stack-md">
        <div className="video-frame">
          <video autoPlay controls playsInline ref={videoRef} />
        </div>
        <div className="status-bar">
          <span className="status-dot" />
          <span>{status}</span>
        </div>
      </div>
    </section>
  );
}
