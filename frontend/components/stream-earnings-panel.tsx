import { formatCurrencyAmount } from "../lib/money";
import type { StreamEarningsSummary } from "../lib/types";

type StreamEarningsPanelProps = {
  earnings: StreamEarningsSummary | null;
  isEnded: boolean;
  isLoading: boolean;
};

function formatDateTime(value: string | null) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString();
}

export function StreamEarningsPanel({
  earnings,
  isEnded,
  isLoading,
}: StreamEarningsPanelProps) {
  return (
    <section className="panel stack-md">
      <div>
        <p className="eyebrow">Earnings</p>
        <h2>{isEnded ? "Final stream earnings" : "Live revenue pulse"}</h2>
      </div>

      {isLoading ? <p className="muted">Loading earnings summary...</p> : null}

      {!isLoading && !earnings ? (
        <p className="muted">No earnings summary is available for this stream yet.</p>
      ) : null}

      {earnings ? (
        <>
          <div className="earnings-hero">
            <span>{isEnded ? "Net earned" : "Net earned so far"}</span>
            <strong>
              {formatCurrencyAmount(earnings.net_earnings_amount, earnings.currency)}
            </strong>
          </div>

          <div className="earnings-grid">
            <div>
              <span>Gross sales</span>
              <strong>
                {formatCurrencyAmount(earnings.gross_sales_amount, earnings.currency)}
              </strong>
            </div>

            <div>
              <span>Platform fees</span>
              <strong>
                {formatCurrencyAmount(earnings.platform_fees_amount, earnings.currency)}
              </strong>
            </div>

            <div>
              <span>Refunded</span>
              <strong>
                {formatCurrencyAmount(earnings.refunded_amount, earnings.currency)}
              </strong>
            </div>

            <div>
              <span>Refund pending</span>
              <strong>
                {formatCurrencyAmount(earnings.refund_pending_amount, earnings.currency)}
              </strong>
            </div>

            <div>
              <span>Paid viewers</span>
              <strong>{earnings.paid_viewer_count}</strong>
            </div>

            <div>
              <span>Total successful payments</span>
              <strong>{earnings.successful_payment_count}</strong>
            </div>

            <div>
              <span>Unique viewers</span>
              <strong>{earnings.viewer_count}</strong>
            </div>

            <div>
              <span>Ticket price</span>
              <strong>
                {earnings.access_type === "paid"
                  ? formatCurrencyAmount(earnings.price_amount, earnings.currency)
                  : "Free"}
              </strong>
            </div>

            <div>
              <span>Last payment</span>
              <strong>{formatDateTime(earnings.last_payment_at)}</strong>
            </div>

            <div>
              <span>Last updated</span>
              <strong>{formatDateTime(earnings.updated_at)}</strong>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

