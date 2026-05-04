"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { RequireAuth } from "../../../components/require-auth";
import { useSession } from "../../../components/session-provider";
import { api } from "../../../lib/api";
import type { StreamRecord } from "../../../lib/types";

type SfuMessage = {
  type: string;
  sdp?: string;
  candidate?: RTCIceCandidateInit | null;
  message?: string;
  reason?: string;
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

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const tokenRef = useRef<string | null>(null);
  const joinedRef = useRef(false);
  const isConnectingRef = useRef(false);

  const [stream, setStream] = useState<StreamRecord | null>(null);
  const [viewerCount, setViewerCount] = useState(0);
  const [status, setStatus] = useState("Loading stream...");
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState(false);

  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  useEffect(() => {
    joinedRef.current = joined;
  }, [joined]);

  useEffect(() => {
    const loadStream = async () => {
      try {
        const response = await api.getStream(streamId);
        setStream(response.stream);
        // use relatime view count
        // setViewerCount(response.viewer_count);

        setStatus(
          response.stream.status === "live"
            ? "Preparing to join SFU room."
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
    if (!token || !stream || !user) {
      return;
    }

    if (stream.status !== "live") {
      return;
    }

    if (stream.broadcaster_id === user.id) {
      return;
    }

    if (joined || isConnectingRef.current) {
      return;
    }

    let cancelled = false;
    isConnectingRef.current = true;

    const connectViewer = async () => {
      try {
        setError(null);

        await api.joinStream(token, streamId);

        if (cancelled) {
          return;
        }

        setStatus("Requesting SFU ticket from main backend...");

        const ticket = await api.getSfuTicket(token, streamId);

        if (cancelled) {
          return;
        }

        const socket = new WebSocket(ticket.sfuUrl);
        socketRef.current = socket;

        socket.onopen = async () => {
          try {
            setStatus("Connected to SFU. Joining as subscriber...");

            socket.send(
              JSON.stringify({
                type: "join",
                roomId: ticket.roomId,
                role: "subscriber",
                token: ticket.token,
              })
            );

            const peer = createPeerConnection();

            const offer = await peer.createOffer();
            await peer.setLocalDescription(offer);

            socket.send(
              JSON.stringify({
                type: "offer",
                sdp: peer.localDescription?.sdp,
              })
            );

            setJoined(true);
            setStatus("Waiting for media from SFU...");
          } catch (openError) {
            const message =
              openError instanceof Error ? openError.message : "Failed to join SFU";
            setError(message);
          }
        };

        socket.onmessage = async (event) => {
          const message = JSON.parse(event.data) as SfuMessage;

          if (message.type === "answer" && message.sdp && peerRef.current) {
            await peerRef.current.setRemoteDescription({
              type: "answer",
              sdp: message.sdp,
            });

            setStatus("Receiving live video.");
          }

          if (message.type === "ice" && message.candidate && peerRef.current) {
            await peerRef.current.addIceCandidate(message.candidate);
          }

          if (message.type === "renegotiate") {
            await renegotiateSubscriber();
          }

          if (message.type === "info") {
            console.log("SFU info:", message.message);
          }

          if (message.type === "error") {
            setError(message.message || "SFU error");
          }
        };

        socket.onerror = () => {
          setError("Viewer SFU websocket error.");
        };

        socket.onclose = () => {
          socketRef.current = null;
          isConnectingRef.current = false;
          setJoined(false);
        };
      } catch (joinError) {
        const message = joinError instanceof Error ? joinError.message : "Unable to join stream";
        setError(message);
      } finally {
        isConnectingRef.current = false;
      }
    };

    void connectViewer();

    return () => {
      cancelled = true;
      isConnectingRef.current = false;
    };
  }, [joined, stream, streamId, token, user]);

  useEffect(() => {
    return () => {
      cleanupViewer();

      if (tokenRef.current && joinedRef.current) {
        void api.leaveStream(tokenRef.current, streamId).catch(() => undefined);
      }
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
      if (socketRef.current?.readyState !== WebSocket.OPEN) {
        return;
      }

      socketRef.current.send(
        JSON.stringify({
          type: "ice",
          candidate: event.candidate ? event.candidate.toJSON() : null,
        })
      );
    };

    peer.onconnectionstatechange = () => {
      setStatus(`Viewer connection state: ${peer.connectionState}`);
    };

    peer.oniceconnectionstatechange = () => {
      console.log("Viewer ICE state:", peer.iceConnectionState);
    };

    peerRef.current = peer;
    return peer;
  };

  const renegotiateSubscriber = async () => {
    const peer = peerRef.current;
    const socket = socketRef.current;

    if (!peer || !socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);

    socket.send(
      JSON.stringify({
        type: "offer",
        sdp: peer.localDescription?.sdp,
      })
    );

    setStatus("Renegotiating media with SFU...");
  };

  const cleanupViewer = () => {
    socketRef.current?.close();
    socketRef.current = null;

    peerRef.current?.close();
    peerRef.current = null;

    remoteStreamRef.current?.getTracks().forEach((track) => track.stop());
    remoteStreamRef.current = null;

    isConnectingRef.current = false;
    setJoined(false);
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