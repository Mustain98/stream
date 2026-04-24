import Link from "next/link";

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
  return (
    <Link className="stream-card" href={href ?? `/watch/${stream.id}`}>
      <div className="card-topline">
        <span className="live-pill">{stream.status}</span>
        <span className="viewer-pill">{stream.viewer_count} watching</span>
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
