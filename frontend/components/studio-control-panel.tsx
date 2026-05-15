import Link from "next/link";

import { BlockedUsersPanel } from "./blocked-users-panel";
import { StreamEarningsPanel } from "./stream-earnings-panel";
import { StreamAccessSettingsPanel } from "./stream-access-settings-panel";
import type {
  BlockedUser,
  StreamAccessResponse,
  StreamEarningsSummary,
  StreamAccessSettingsPayload,
  StreamRecord,
  StripeConnectStatus,
} from "../lib/types";

type StudioControlsPanelProps = {
  stream: StreamRecord;

  isLive: boolean;
  isEnded: boolean;
  canGoLive: boolean;
  isUpdatingStream: boolean;

  publisherIsConnecting: boolean;
  publisherIsConnected: boolean;
  publisherIsReconnecting: boolean;
  publisherReconnectFailed: boolean;

  publisherIsPaused: boolean;
  publisherIsCameraEnabled: boolean;
  publisherIsMicEnabled: boolean;

  viewerCount: number;

  blockedUsers: BlockedUser[];
  isLoadingBlockedUsers: boolean;

  access: StreamAccessResponse | null;
  isLoadingAccess: boolean;
  earnings: StreamEarningsSummary | null;
  isLoadingEarnings: boolean;

  stripeStatus: StripeConnectStatus | null;
  isLoadingStripeStatus: boolean;

  onGoLive: () => void;
  onEndLive: () => void;
  onTryAgain: () => void;
  onUnblockViewer: (userId: string) => void;
  onSaveAccess: (payload: StreamAccessSettingsPayload) => Promise<void>;
};

function formatDateTime(value: string | null) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString();
}

export function StudioControlsPanel({
  stream,
  isLive,
  isEnded,
  canGoLive,
  isUpdatingStream,
  publisherIsConnecting,
  publisherIsConnected,
  publisherIsReconnecting,
  publisherReconnectFailed,
  publisherIsPaused,
  publisherIsCameraEnabled,
  publisherIsMicEnabled,
  viewerCount,
  blockedUsers,
  isLoadingBlockedUsers,
  access,
  isLoadingAccess,
  earnings,
  isLoadingEarnings,
  stripeStatus,
  isLoadingStripeStatus,
  onGoLive,
  onEndLive,
  onTryAgain,
  onUnblockViewer,
  onSaveAccess,
}: StudioControlsPanelProps) {
  return (
    <div className="panel stack-md">
      <div>
        <p className="eyebrow">Broadcast controls</p>
        <h2>{isEnded ? "Stream summary" : "Manage this room"}</h2>
      </div>

      <div className="stack-sm">
        {canGoLive ? (
          <button
            className="primary-button"
            disabled={isUpdatingStream || publisherIsConnecting}
            onClick={onGoLive}
            type="button"
          >
            {isUpdatingStream || publisherIsConnecting ? "Going live..." : "Go Live"}
          </button>
        ) : null}

        {isLive ? (
          <button
            className="ghost-button danger"
            disabled={isUpdatingStream}
            onClick={onEndLive}
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

        {publisherReconnectFailed && isLive && !isEnded ? (
          <button className="primary-button" onClick={onTryAgain} type="button">
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
                {publisherIsConnected
                  ? "connected"
                  : publisherIsReconnecting
                    ? "reconnecting"
                    : "not connected"}
              </strong>
            </div>

            <div>
              <span>Camera</span>
              <strong>{publisherIsCameraEnabled ? "on" : "off"}</strong>
            </div>

            <div>
              <span>Mic</span>
              <strong>{publisherIsMicEnabled ? "on" : "muted"}</strong>
            </div>

            <div>
              <span>Playback</span>
              <strong>{publisherIsPaused ? "paused" : "live"}</strong>
            </div>
          </>
        )}

        <div>
          <span>Stripe</span>
          <strong>{stripeStatus?.onboarding_completed ? "ready" : "not ready"}</strong>
        </div>

        <div>
          <span>Stream ID</span>
          <strong>{stream.id}</strong>
        </div>
      </div>

      <StreamAccessSettingsPanel
        access={access}
        isLoading={isLoadingAccess}
        stripeStatus={stripeStatus}
        isLoadingStripeStatus={isLoadingStripeStatus}
        onSave={onSaveAccess}
      />

      <StreamEarningsPanel
        earnings={earnings}
        isEnded={isEnded}
        isLoading={isLoadingEarnings}
      />

      <BlockedUsersPanel
        blockedUsers={blockedUsers}
        isLoading={isLoadingBlockedUsers}
        onUnblock={onUnblockViewer}
      />
    </div>
  );
}
