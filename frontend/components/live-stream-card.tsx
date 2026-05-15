import Link from "next/link";

import { formatCurrencyAmount } from "../lib/money";
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
  const netEarnings = stream.earnings_summary?.net_earnings_amount;
  const earningsCurrency = stream.earnings_summary?.currency ?? "usd";

  return (
    <Link className="stream-card" href={href ?? `/watch/${stream.id}`}>
      <div className="card-topline">
        <span className={isLive ? "live-pill active" : "live-pill"}>
          {formatStreamStatus(stream.status)}
        </span>

        <div className="stream-card-pills">
          {shouldShowViewerCount ? (
            <span className="viewer-pill">{stream.viewer_count} viewers</span>
          ) : null}

          {typeof netEarnings === "number" ? (
            <span className="earnings-pill">
              Earned {formatCurrencyAmount(netEarnings, earningsCurrency)}
            </span>
          ) : null}
        </div>
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
