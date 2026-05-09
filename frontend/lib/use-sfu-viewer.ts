"use client";

import { RefObject, useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";
import type { SfuMessage, ViewerInfo } from "./types";

type Options = {
  token: string | null;
  streamId: string;
  enabled: boolean;
  videoRef: RefObject<HTMLVideoElement | null>;
};

export function useSfuViewer({ token, streamId, enabled, videoRef }: Options) {
  const socketRef = useRef<WebSocket | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const joinedRef = useRef(false);
  const connectingRef = useRef(false);

  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [viewerCount, setViewerCount] = useState(0);
  const [viewers, setViewers] = useState<ViewerInfo[]>([]);
  const [status, setStatus] = useState("Not connected.");
  const [error, setError] = useState<string | null>(null);

  const disconnect = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;

    peerRef.current?.close();
    peerRef.current = null;

    remoteStreamRef.current?.getTracks().forEach((track) => {
      track.stop();
    });

    remoteStreamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    if (token && joinedRef.current) {
      void api.leaveStream(token, streamId).catch(() => undefined);
    }

    joinedRef.current = false;
    connectingRef.current = false;

    setIsConnected(false);
    setIsPaused(false);
    setViewerCount(0);
    setViewers([]);
  }, [streamId, token, videoRef]);

  const createPeerConnection = useCallback(() => {
    const peer = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

    peer.addTransceiver("video", { direction: "recvonly" });
    peer.addTransceiver("audio", { direction: "recvonly" });

    peer.ontrack = (event) => {
      if (!remoteStreamRef.current) {
        remoteStreamRef.current = new MediaStream();
      }

      const trackExists = remoteStreamRef.current
        .getTracks()
        .some((track) => track.id === event.track.id);

      if (!trackExists) {
        remoteStreamRef.current.addTrack(event.track);
      }

      if (videoRef.current) {
        videoRef.current.srcObject = remoteStreamRef.current;
        void videoRef.current.play().catch(() => undefined);
      }
    };

    peer.onicecandidate = (event) => {
      if (socketRef.current?.readyState !== WebSocket.OPEN) return;

      socketRef.current.send(
        JSON.stringify({
          type: "ice",
          candidate: event.candidate ? event.candidate.toJSON() : null,
        })
      );
    };

    peer.onconnectionstatechange = () => {
      setStatus(`Viewer connection: ${peer.connectionState}`);

      if (peer.connectionState === "connected") {
        setIsConnected(true);
      }

      if (
        peer.connectionState === "failed" ||
        peer.connectionState === "closed" ||
        peer.connectionState === "disconnected"
      ) {
        setIsConnected(false);
      }
    };

    peerRef.current = peer;
    return peer;
  }, [videoRef]);

  const renegotiate = useCallback(async () => {
    const peer = peerRef.current;
    const socket = socketRef.current;

    if (!peer || !socket || socket.readyState !== WebSocket.OPEN) return;

    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);

    socket.send(
      JSON.stringify({
        type: "offer",
        sdp: peer.localDescription?.sdp,
      })
    );

    setStatus("Renegotiating stream...");
  }, []);

  const connect = useCallback(async () => {
    if (!token || connectingRef.current || socketRef.current) return;

    connectingRef.current = true;

    try {
      setError(null);

      await api.joinStream(token, streamId);
      joinedRef.current = true;

      setStatus("Requesting stream ticket...");

      const ticket = await api.getSfuTicket(token, streamId);
      const socket = new WebSocket(ticket.sfuUrl);
      socketRef.current = socket;

      socket.onopen = async () => {
        try {
          setStatus("Connecting to stream...");

          socket.send(
            JSON.stringify({
              type: "join",
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

          setStatus("Waiting for video...");
        } catch (openError) {
          const message =
            openError instanceof Error ? openError.message : "Failed to connect stream";

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

          setStatus(isPaused ? "Stream paused." : "Watching live.");
        }

        if (message.type === "ice" && message.candidate && peerRef.current) {
          await peerRef.current.addIceCandidate(message.candidate);
        }

        if (message.type === "renegotiate") {
          await renegotiate();
        }

        if (message.type === "presence") {
          setViewerCount(message.viewerCount ?? 0);
          setViewers(message.viewers ?? []);
        }

        if (message.type === "stream-state") {
          const paused = message.state === "paused";
          setIsPaused(paused);
          setStatus(paused ? "Stream paused." : "Watching live.");
        }

        if (message.type === "error") {
          setError(message.message || "Stream server error");
        }
      };

      socket.onerror = () => {
        setError("Stream connection error.");
      };

      socket.onclose = () => {
        socketRef.current = null;
        connectingRef.current = false;
        setIsConnected(false);
        setIsPaused(false);
      };
    } catch (connectError) {
      const message =
        connectError instanceof Error ? connectError.message : "Unable to join stream";

      setError(message);
      disconnect();
    } finally {
      connectingRef.current = false;
    }
  }, [token, streamId, createPeerConnection, disconnect, isPaused, renegotiate]);

  useEffect(() => {
    if (enabled) {
      void connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    isPaused,
    viewerCount,
    viewers,
    status,
    error,
    setError,
    connect,
    disconnect,
  };
}