"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
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
  const mediaRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);

  const [stream, setStream] = useState<StreamRecord | null>(null);
  const [viewerCount, setViewerCount] = useState(0);
  const [status, setStatus] = useState("Loading room...");
  const [error, setError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [isConnectedToSfu, setIsConnectedToSfu] = useState(false);

  const isOwner = stream?.broadcaster_id === user?.id;

  useEffect(() => {
    const loadRoom = async () => {
      try {
        const response = await api.getStream(streamId);
        setStream(response.stream);
        setViewerCount(response.viewer_count);

        setStatus(
          response.stream.status === "live"
            ? "Stream is live. Enable camera to publish to the SFU."
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
    return () => {
      cleanupSfu();
      mediaRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const createPeerConnection = () => {
    const peer = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

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
      setStatus(`SFU connection state: ${peer.connectionState}`);

      if (
        peer.connectionState === "failed" ||
        peer.connectionState === "closed" ||
        peer.connectionState === "disconnected"
      ) {
        setIsConnectedToSfu(false);
      }
    };

    peer.oniceconnectionstatechange = () => {
      console.log("Publisher ICE state:", peer.iceConnectionState);
    };

    mediaRef.current?.getTracks().forEach((track) => {
      if (mediaRef.current) {
        peer.addTrack(track, mediaRef.current);
      }
    });

    peerRef.current = peer;
    return peer;
  };

  const connectPublisherToSfu = async () => {
    if (!token) {
      setError("Missing auth token.");
      return;
    }

    if (!mediaRef.current) {
      setError("Enable camera before connecting to SFU.");
      return;
    }

    if (!stream || stream.status !== "live") {
      setError("Start the stream before connecting to SFU.");
      return;
    }

    if (!isOwner) {
      setError("Only the broadcaster can publish this stream.");
      return;
    }

    if (socketRef.current || peerRef.current) {
      return;
    }

    try {
      setError(null);
      setStatus("Requesting SFU ticket from main backend...");

      const ticket = await api.getSfuTicket(token, streamId);

      const socket = new WebSocket(ticket.sfuUrl);
      socketRef.current = socket;

      socket.onopen = async () => {
        try {
          setStatus("Connected to SFU. Joining as publisher...");

          socket.send(
            JSON.stringify({
              type: "join",
              roomId: ticket.roomId,
              role: "publisher",
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

          setIsConnectedToSfu(true);
          setStatus("Publishing media to SFU...");
        } catch (openError) {
          const message =
            openError instanceof Error ? openError.message : "Failed to publish to SFU";
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

          setStatus("Live media is connected to SFU.");
        }

        if (message.type === "ice" && message.candidate && peerRef.current) {
          await peerRef.current.addIceCandidate(message.candidate);
        }

        if (message.type === "info") {
          console.log("SFU info:", message.message);
        }

        if (message.type === "error") {
          setError(message.message || "SFU error");
        }
      };

      socket.onerror = () => {
        setError("SFU websocket error.");
        setIsConnectedToSfu(false);
      };

      socket.onclose = () => {
        setStatus("Disconnected from SFU.");
        setIsConnectedToSfu(false);
        socketRef.current = null;
      };
    } catch (connectError) {
      const message =
        connectError instanceof Error ? connectError.message : "Failed to connect to SFU";
      setError(message);
      cleanupSfu();
    }
  };

  const cleanupSfu = () => {
    socketRef.current?.close();
    socketRef.current = null;

    peerRef.current?.close();
    peerRef.current = null;

    setIsConnectedToSfu(false);
  };

  const enableCamera = async () => {
    try {
      setError(null);

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
      setStatus("Stream is now live. Enable camera, then connect to SFU.");
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

      cleanupSfu();

      mediaRef.current?.getTracks().forEach((track) => track.stop());
      mediaRef.current = null;
      setCameraReady(false);

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
                className="ghost-button"
                disabled={!cameraReady || stream.status !== "live" || isConnectedToSfu}
                onClick={connectPublisherToSfu}
                type="button"
              >
                {isConnectedToSfu ? "Connected to SFU" : "Connect to SFU"}
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
                <span>SFU</span>
                <strong>{isConnectedToSfu ? "connected" : "not connected"}</strong>
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