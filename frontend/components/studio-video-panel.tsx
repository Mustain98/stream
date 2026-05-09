import type { RefObject } from "react";

import type { ViewerInfo } from "../lib/types";

type StudioVideoPanelProps = {
  videoRef: RefObject<HTMLVideoElement | null>;

  isLive: boolean;
  isEnded: boolean;
  cameraReady: boolean;

  isPaused: boolean;
  isConnected: boolean;
  isCameraEnabled: boolean;
  isMicEnabled: boolean;

  status: string;
  reconnectFailed: boolean;

  viewerCount: number;
  viewers: ViewerInfo[];

  onTogglePause: () => void;
  onToggleCamera: () => void;
  onToggleMic: () => void;
  onBlockViewer: (userId: string | null, username: string) => void;
};

export function StudioVideoPanel({
  videoRef,
  isLive,
  isEnded,
  cameraReady,
  isPaused,
  isConnected,
  isCameraEnabled,
  isMicEnabled,
  status,
  reconnectFailed,
  viewerCount,
  viewers,
  onTogglePause,
  onToggleCamera,
  onToggleMic,
  onBlockViewer,
}: StudioVideoPanelProps) {
  return (
    <div className="panel stack-md">
      <div className="video-frame">
        <video autoPlay muted playsInline ref={videoRef} />

        {isPaused && isLive ? (
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
            aria-label={isPaused ? "Resume stream" : "Pause stream"}
            className={isPaused ? "resource-button active" : "resource-button"}
            disabled={!cameraReady || !isConnected}
            onClick={onTogglePause}
            title={isPaused ? "Resume stream" : "Pause stream"}
            type="button"
          >
            {isPaused ? "▶" : "⏸"}
          </button>

          <button
            aria-label={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
            className={isCameraEnabled ? "resource-button" : "resource-button muted"}
            disabled={!cameraReady || isPaused}
            onClick={onToggleCamera}
            title={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
            type="button"
          >
            {isCameraEnabled ? "🎥" : "🚫"}
          </button>

          <button
            aria-label={isMicEnabled ? "Mute mic" : "Unmute mic"}
            className={isMicEnabled ? "resource-button" : "resource-button muted"}
            disabled={!cameraReady || isPaused}
            onClick={onToggleMic}
            title={isMicEnabled ? "Mute mic" : "Unmute mic"}
            type="button"
          >
            {isMicEnabled ? "🎙" : "🔇"}
          </button>
        </div>
      ) : null}

      <div className="status-bar">
        <span className="status-dot" />
        <span>{status}</span>
      </div>

      {reconnectFailed && isLive && !isEnded ? (
        <div className="error-banner">
          <strong>Connection lost.</strong> Your stream may still be live for a short time.
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
                  <div>
                    <strong>{viewer.username}</strong>
                    <span>{viewer.userId}</span>
                  </div>

                  {viewer.userId ? (
                    <button
                      className="mini-danger-button"
                      onClick={() => onBlockViewer(viewer.userId, viewer.username)}
                      type="button"
                    >
                      Block
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )
        ) : (
          <p className="muted">This viewer count is loaded from the saved stream record.</p>
        )}
      </div>
    </div>
  );
}