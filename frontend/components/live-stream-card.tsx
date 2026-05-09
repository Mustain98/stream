import Link from "next/link";

import { formatStreamStatus, isLiveStatus } from "../lib/stream-utils";
import type { StreamSummary } from "../lib/types";

export function LiveStreamCard({
  stream,
  href,
  ctaLabel = "Open stream",
}: {
  stream: StreamSummary;
  href?: string;
  ctaLabel?: string;
}) {
  const isLive = isLiveStatus(stream.status);
  const shouldShowViewerCount =
    !isLive && typeof stream.viewer_count === "number";

  return (
    <Link className="stream-card" href={href ?? `/watch/${stream.id}`}>
      <div className="card-topline">
        <span className={isLive ? "live-pill active" : "live-pill"}>
          {formatStreamStatus(stream.status)}
        </span>

        {shouldShowViewerCount ? (
          <span className="viewer-pill">{stream.viewer_count} viewers</span>
        ) : null}
      </div>

      <h2>{stream.title}</h2>

      <p className="muted">{stream.description || "No description yet."}</p>

      <div className="card-footer">
        <span>{ctaLabel}</span>
        <strong>{stream.id.slice(0, 8)}</strong>
      </div>
    </Link>
  );
}