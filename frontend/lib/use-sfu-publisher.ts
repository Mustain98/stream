"use client";

import { useCallback, useRef, useState } from "react";

import { api } from "./api";
import { appendChatMessage } from "./stream-chat";
import type {
  SfuMessage,
  StreamChatMessage,
  StreamEarningsSummary,
  ViewerInfo,
} from "./types";

type ConnectOptions = {
  mediaStream: MediaStream;
  isPaused?: boolean;
  isMicEnabled?: boolean;
  isCameraEnabled?: boolean;
};

type Options = {
  token: string | null;
  streamId: string;
};

// Use shorter delays while testing.
// Later change back to [0, 2_000, 5_000, 10_000, 15_000]
const AUTO_RECONNECT_DELAYS_MS = [0, 1_000, 2_000];

export function useSfuPublisher({ token, streamId }: Options) {
  const socketRef = useRef<WebSocket | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const latestMediaRef = useRef<MediaStream | null>(null);

  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const shouldAutoReconnectRef = useRef(false);
  const isConnectingRef = useRef(false);
  const intentionalCloseRef = useRef(false);
  const reconnectScheduledRef = useRef(false);

  const connectRef = useRef<((options: ConnectOptions) => Promise<boolean>) | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [reconnectFailed, setReconnectFailed] = useState(false);

  const [isPaused, setIsPaused] = useState(false);
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [isCameraEnabled, setIsCameraEnabled] = useState(true);

  const [viewerCount, setViewerCount] = useState(0);
  const [viewers, setViewers] = useState<ViewerInfo[]>([]);
  const [chatMessages, setChatMessages] = useState<StreamChatMessage[]>([]);
  const [earningsSummary, setEarningsSummary] = useState<StreamEarningsSummary | null>(null);

  const [status, setStatus] = useState("Not connected.");
  const [error, setError] = useState<string | null>(null);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimeoutRef.current !== null) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    reconnectScheduledRef.current = false;
  }, []);

  const closeConnectionOnly = useCallback((intentional = true) => {
    const socket = socketRef.current;
    const peer = peerRef.current;

    intentionalCloseRef.current = intentional;

    socketRef.current = null;
    peerRef.current = null;

    if (peer) {
      peer.close();
    }

    if (socket && socket.readyState !== WebSocket.CLOSED) {
      socket.close();
    }

    window.setTimeout(() => {
      intentionalCloseRef.current = false;
    }, 0);

    setIsConnected(false);
  }, []);

  const markReconnectFailed = useCallback(
    (message = "Could not reconnect.") => {
      clearReconnectTimer();

      reconnectAttemptsRef.current = AUTO_RECONNECT_DELAYS_MS.length;
      reconnectScheduledRef.current = false;

      setIsConnected(false);
      setIsConnecting(false);
      setIsReconnecting(false);
      setReconnectFailed(true);
      setStatus(message);
    },
    [clearReconnectTimer]
  );

  const cleanup = useCallback(() => {
    shouldAutoReconnectRef.current = false;
    isConnectingRef.current = false;
    reconnectAttemptsRef.current = 0;

    clearReconnectTimer();
    closeConnectionOnly(true);

    setIsConnected(false);
    setIsConnecting(false);
    setIsReconnecting(false);
    setReconnectFailed(false);

    setIsPaused(false);
    setViewerCount(0);
    setViewers([]);

    setStatus("Not connected.");
  }, [clearReconnectTimer, closeConnectionOnly]);

  const applyTrackState = useCallback(
    (
      mediaStream: MediaStream,
      nextPaused = isPaused,
      nextMicEnabled = isMicEnabled,
      nextCameraEnabled = isCameraEnabled
    ) => {
      mediaStream.getAudioTracks().forEach((track) => {
        track.enabled = nextPaused ? false : nextMicEnabled;
      });

      mediaStream.getVideoTracks().forEach((track) => {
        track.enabled = nextPaused ? false : nextCameraEnabled;
      });
    },
    [isCameraEnabled, isMicEnabled, isPaused]
  );

  const sendStreamState = useCallback((state: "live" | "paused") => {
    const socket = socketRef.current;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    socket.send(
      JSON.stringify({
        type: "stream-state",
        state,
      })
    );
  }, []);

  const sendChat = useCallback(async (message: string) => {
    const socket = socketRef.current;
    const trimmedMessage = message.trim();

    if (!trimmedMessage) {
      return false;
    }

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false;
    }

    socket.send(
      JSON.stringify({
        type: "chat",
        message: trimmedMessage,
      })
    );

    return true;
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (!shouldAutoReconnectRef.current) {
      return;
    }

    if (reconnectScheduledRef.current) {
      return;
    }

    const mediaStream = latestMediaRef.current;

    if (!mediaStream) {
      markReconnectFailed("Could not reconnect. Camera is not available.");
      return;
    }

    closeConnectionOnly(true);
    clearReconnectTimer();

    const attempt = reconnectAttemptsRef.current;

    if (attempt >= AUTO_RECONNECT_DELAYS_MS.length) {
      markReconnectFailed("Could not reconnect.");
      return;
    }

    const delay = AUTO_RECONNECT_DELAYS_MS[attempt];

    reconnectAttemptsRef.current += 1;
    reconnectScheduledRef.current = true;

    setIsReconnecting(true);
    setReconnectFailed(false);
    setStatus("Reconnecting broadcast...");

    reconnectTimeoutRef.current = window.setTimeout(() => {
      reconnectScheduledRef.current = false;

      void connectRef.current?.({
        mediaStream,
        isPaused,
        isMicEnabled,
        isCameraEnabled,
      });
    }, delay);
  }, [
    clearReconnectTimer,
    closeConnectionOnly,
    isCameraEnabled,
    isMicEnabled,
    isPaused,
    markReconnectFailed,
  ]);

  const connect = useCallback(
    async ({
      mediaStream,
      isPaused: requestedPaused,
      isMicEnabled: requestedMicEnabled,
      isCameraEnabled: requestedCameraEnabled,
    }: ConnectOptions) => {
      if (!token) {
        setError("Missing auth token.");
        return false;
      }

      if (isConnectingRef.current || socketRef.current || peerRef.current) {
        return true;
      }

      latestMediaRef.current = mediaStream;

      const nextPaused = requestedPaused ?? isPaused;
      const nextMicEnabled = requestedMicEnabled ?? isMicEnabled;
      const nextCameraEnabled = requestedCameraEnabled ?? isCameraEnabled;

      applyTrackState(mediaStream, nextPaused, nextMicEnabled, nextCameraEnabled);

      isConnectingRef.current = true;
      shouldAutoReconnectRef.current = true;

      setIsConnecting(true);
      setReconnectFailed(false);
      setError(null);

      try {
        setStatus("Requesting stream ticket...");

        const ticket = await api.getSfuTicket(token, streamId);
        const socket = new WebSocket(ticket.sfuUrl);

        socketRef.current = socket;

        socket.onopen = async () => {
          try {
            setStatus("Connecting broadcast...");

            socket.send(
              JSON.stringify({
                type: "join",
                token: ticket.token,
              })
            );

            const peer = new RTCPeerConnection({
              iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
            });

            peer.onicecandidate = (event) => {
              if (socket.readyState !== WebSocket.OPEN) {
                return;
              }

              socket.send(
                JSON.stringify({
                  type: "ice",
                  candidate: event.candidate ? event.candidate.toJSON() : null,
                })
              );
            };

            peer.onconnectionstatechange = () => {
              if (peer.connectionState === "connected") {
                reconnectAttemptsRef.current = 0;
                reconnectScheduledRef.current = false;

                setIsConnected(true);
                setIsConnecting(false);
                setIsReconnecting(false);
                setReconnectFailed(false);
                setStatus(nextPaused ? "Stream paused." : "Broadcasting.");
              }

              if (
                peer.connectionState === "failed" ||
                peer.connectionState === "disconnected"
              ) {
                setIsConnected(false);
                setStatus("Broadcast connection interrupted.");

                if (shouldAutoReconnectRef.current) {
                  scheduleReconnect();
                }
              }

              if (peer.connectionState === "closed") {
                setIsConnected(false);
              }
            };

            mediaStream.getTracks().forEach((track) => {
              peer.addTrack(track, mediaStream);
            });

            peerRef.current = peer;

            const offer = await peer.createOffer();
            await peer.setLocalDescription(offer);

            socket.send(
              JSON.stringify({
                type: "offer",
                sdp: peer.localDescription?.sdp,
              })
            );

            if (nextPaused) {
              sendStreamState("paused");
            }
          } catch (openError) {
            const message =
              openError instanceof Error
                ? openError.message
                : "Failed to connect broadcast";

            setError(message);
            scheduleReconnect();
          }
        };

        socket.onmessage = async (event) => {
          const message = JSON.parse(event.data) as SfuMessage;

          if (message.type === "answer" && message.sdp && peerRef.current) {
            await peerRef.current.setRemoteDescription({
              type: "answer",
              sdp: message.sdp,
            });

            setStatus(nextPaused ? "Stream paused." : "Broadcasting.");
          }

          if (message.type === "ice" && message.candidate && peerRef.current) {
            await peerRef.current.addIceCandidate(message.candidate);
          }

          if (message.type === "presence") {
            setViewerCount(message.viewerCount ?? 0);
            setViewers(message.viewers ?? []);
          }

          if (message.type === "stream-state") {
            const paused = message.state === "paused";

            setIsPaused(paused);
            setStatus(paused ? "Stream paused." : "Broadcasting.");
          }

          if (message.type === "earnings-update" && message.summary) {
            setEarningsSummary(message.summary);
          }

          const chatPeerId = message.peerId;
          const chatUsername = message.username;
          const chatText = message.message;

          if (message.type === "chat" && chatPeerId && chatUsername && chatText) {
            setChatMessages((currentMessages) =>
              appendChatMessage(currentMessages, {
                id: `${chatPeerId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                roomId: message.roomId,
                peerId: chatPeerId,
                userId: message.userId ?? null,
                username: chatUsername,
                role: message.role,
                message: chatText,
                mentions: message.mentions ?? [],
                receivedAt: new Date().toISOString(),
              })
            );
          }

          if (message.type === "error") {
            setError(message.message || "Stream server error");
          }
        };

        socket.onerror = () => {
          setError("Broadcast connection error.");
          setIsConnected(false);

          if (shouldAutoReconnectRef.current) {
            scheduleReconnect();
          } else {
            markReconnectFailed("Could not connect to broadcast server.");
          }
        };

        socket.onclose = () => {
          if (socketRef.current === socket) {
            socketRef.current = null;
          }

          setIsConnected(false);

          if (!intentionalCloseRef.current && shouldAutoReconnectRef.current) {
            setStatus("Broadcast disconnected.");
            scheduleReconnect();
          }
        };

        return true;
      } catch (connectError) {
        const message =
          connectError instanceof Error ? connectError.message : "Failed to connect";

        setError(message);

        if (shouldAutoReconnectRef.current) {
          scheduleReconnect();
        } else {
          markReconnectFailed(message);
        }

        return false;
      } finally {
        isConnectingRef.current = false;
        setIsConnecting(false);
      }
    },
    [
      token,
      streamId,
      isPaused,
      isMicEnabled,
      isCameraEnabled,
      applyTrackState,
      sendStreamState,
      scheduleReconnect,
      markReconnectFailed,
    ]
  );

  connectRef.current = connect;

  const tryAgain = useCallback(async () => {
    const mediaStream = latestMediaRef.current;

    if (!mediaStream) {
      setError("Camera is not available.");
      return false;
    }

    reconnectAttemptsRef.current = 0;
    reconnectScheduledRef.current = false;

    setReconnectFailed(false);
    setIsReconnecting(false);

    closeConnectionOnly(true);

    return connect({
      mediaStream,
      isPaused,
      isMicEnabled,
      isCameraEnabled,
    });
  }, [closeConnectionOnly, connect, isCameraEnabled, isMicEnabled, isPaused]);

  const disconnect = useCallback(() => {
    shouldAutoReconnectRef.current = false;
    clearReconnectTimer();
    closeConnectionOnly(true);

    setIsConnecting(false);
    setIsReconnecting(false);
    setReconnectFailed(false);
    setStatus("Disconnected.");
  }, [clearReconnectTimer, closeConnectionOnly]);

  const togglePause = useCallback(() => {
    const mediaStream = latestMediaRef.current;

    if (!mediaStream) {
      setError("Camera/mic is not enabled.");
      return;
    }

    const nextPaused = !isPaused;

    applyTrackState(mediaStream, nextPaused, isMicEnabled, isCameraEnabled);

    setIsPaused(nextPaused);
    sendStreamState(nextPaused ? "paused" : "live");
    setStatus(nextPaused ? "Stream paused." : "Broadcasting.");
  }, [applyTrackState, isCameraEnabled, isMicEnabled, isPaused, sendStreamState]);

  const toggleMic = useCallback(() => {
    const mediaStream = latestMediaRef.current;

    if (!mediaStream) {
      setError("Camera/mic is not enabled.");
      return;
    }

    const nextEnabled = !isMicEnabled;

    mediaStream.getAudioTracks().forEach((track) => {
      track.enabled = isPaused ? false : nextEnabled;
    });

    setIsMicEnabled(nextEnabled);
  }, [isMicEnabled, isPaused]);

  const toggleCamera = useCallback(() => {
    const mediaStream = latestMediaRef.current;

    if (!mediaStream) {
      setError("Camera/mic is not enabled.");
      return;
    }

    const nextEnabled = !isCameraEnabled;

    mediaStream.getVideoTracks().forEach((track) => {
      track.enabled = isPaused ? false : nextEnabled;
    });

    setIsCameraEnabled(nextEnabled);
  }, [isCameraEnabled, isPaused]);

  const setMediaStream = useCallback(
    (mediaStream: MediaStream | null) => {
      latestMediaRef.current = mediaStream;

      if (mediaStream) {
        applyTrackState(mediaStream);
      }
    },
    [applyTrackState]
  );

  return {
    isConnected,
    isConnecting,
    isReconnecting,
    reconnectFailed,

    isPaused,
    isMicEnabled,
    isCameraEnabled,

    viewerCount,
    viewers,
    chatMessages,
    earningsSummary,

    status,
    error,
    setError,

    connect,
    disconnect,
    cleanup,
    tryAgain,

    togglePause,
    toggleMic,
    toggleCamera,
    sendChat,
    setMediaStream,
  };
}
