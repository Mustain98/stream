"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EarningsBarChart } from "../../components/earnings-bar-chart";
import { LiveStreamCard } from "../../components/live-stream-card";
import { RequireAuth } from "../../components/require-auth";
import { useSession } from "../../components/session-provider";
import { api } from "../../lib/api";
import { formatCurrencyAmount } from "../../lib/money";
import type { EarningsHistoryResponse, SpendHistoryResponse } from "../../lib/types";
import { useUserDashboard } from "../../lib/use-user-dashboard";

// ── helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function periodLabel(period: string) {
  if (period.length === 7) {
    const [y, m] = period.split("-");
    return new Date(Number(y), Number(m) - 1).toLocaleString("default", {
      month: "long",
      year: "numeric",
    });
  }
  return period;
}

function streamFallbackDate(stream: { started_at: string | null; created_at?: string }) {
  return stream.started_at ?? stream.created_at ?? null;
}

function matchesPeriod(dateStr: string | null, year: number, month: number): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  if (d.getFullYear() !== year) return false;
  if (month > 0 && d.getMonth() + 1 !== month) return false;
  return true;
}

// ── static options ────────────────────────────────────────────────────────────

const NOW = new Date();
const CURRENT_YEAR = NOW.getFullYear();
const CURRENT_MONTH = NOW.getMonth() + 1;

const YEARS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i);
const MONTHS = [
  { value: 0, label: "All months" },
  { value: 1, label: "January" },
  { value: 2, label: "February" },
  { value: 3, label: "March" },
  { value: 4, label: "April" },
  { value: 5, label: "May" },
  { value: 6, label: "June" },
  { value: 7, label: "July" },
  { value: 8, label: "August" },
  { value: 9, label: "September" },
  { value: 10, label: "October" },
  { value: 11, label: "November" },
  { value: 12, label: "December" },
];

// ── page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfileContent />
    </RequireAuth>
  );
}

function ProfileContent() {
  const { token, user, refreshUser } = useSession();
  const userDashboard = useUserDashboard({ token });

  // account form
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // single period selector — controls earnings, spend, and stream list
  const [selectedYear, setSelectedYear] = useState(CURRENT_YEAR);
  const [selectedMonth, setSelectedMonth] = useState(CURRENT_MONTH);

  const [earningsHistory, setEarningsHistory] = useState<EarningsHistoryResponse | null>(null);
  const [isLoadingEarnings, setIsLoadingEarnings] = useState(false);

  const [spendHistory, setSpendHistory] = useState<SpendHistoryResponse | null>(null);
  const [isLoadingSpend, setIsLoadingSpend] = useState(false);

  useEffect(() => {
    setUsername(user?.username ?? "");
    setEmail(user?.email ?? "");
  }, [user?.username, user?.email]);

  useEffect(() => {
    if (!token) return;
    void userDashboard.loadDashboard();
  }, [token, userDashboard.loadDashboard]);

  const loadEarningsHistory = useCallback(async () => {
    if (!token) return;
    setIsLoadingEarnings(true);
    try {
      const data = await api.getEarningsHistory(token, selectedYear, selectedMonth || undefined);
      setEarningsHistory(data);
    } finally {
      setIsLoadingEarnings(false);
    }
  }, [token, selectedYear, selectedMonth]);

  const loadSpendHistory = useCallback(async () => {
    if (!token) return;
    setIsLoadingSpend(true);
    try {
      const data = await api.getSpendHistory(token, selectedYear, selectedMonth || undefined);
      setSpendHistory(data);
    } finally {
      setIsLoadingSpend(false);
    }
  }, [token, selectedYear, selectedMonth]);

  useEffect(() => { void loadEarningsHistory(); }, [loadEarningsHistory]);
  useEffect(() => { void loadSpendHistory(); }, [loadSpendHistory]);

  const handleSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setMessage(null);
    setFormError(null);
    try {
      await api.updateMe(token, { username: username.trim(), email: email.trim() || null });
      await refreshUser();
      await userDashboard.loadDashboard();
      setMessage("Account details updated.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to update account");
    } finally {
      setIsSaving(false);
    }
  };

  const dashboard = userDashboard.dashboard;
  const stripeStatus = dashboard?.stripe_status;
  const stripeReady = Boolean(stripeStatus?.onboarding_completed);
  const recentPurchases = dashboard?.recent_purchases ?? [];

  // filter streams by the selected period
  const allStreams = dashboard?.owned_streams ?? [];
  const filteredStreams = allStreams.filter((s) =>
    matchesPeriod(streamFallbackDate(s), selectedYear, selectedMonth)
  );

  const isCurrentPeriod =
    selectedYear === CURRENT_YEAR && (selectedMonth === 0 || selectedMonth === CURRENT_MONTH);

  // current-month snapshot from dashboard (always "this month")
  const snapBroadcaster = dashboard?.broadcaster_stats;
  const snapViewer = dashboard?.viewer_stats;

  return (
    <section className="stack-xl">
      {/* Hero */}
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Account dashboard</p>
          <h1>Streams, earnings, and spend — all in one place.</h1>
        </div>
        <div className="stat-block">
          <span>Signed in as</span>
          <strong>{user?.username}</strong>
        </div>
      </div>

      {userDashboard.dashboardError ? (
        <p className="error-banner">{userDashboard.dashboardError}</p>
      ) : null}

      {/* Account + current-month snapshot */}
      <div className="studio-grid">
        <form className="panel stack-md" onSubmit={handleSubmit}>
          <div>
            <p className="eyebrow">Profile</p>
            <h2>Account details</h2>
          </div>
          <label className="field">
            <span>Username</span>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)} />
          </label>
          <div className="meta-list">
            <div><span>User ID</span><strong>{user?.id ?? "—"}</strong></div>
            <div><span>Joined</span><strong>{formatDateTime(user?.created_at)}</strong></div>
            <div><span>Status</span><strong>{user?.is_active ? "active" : "inactive"}</strong></div>
          </div>
          {message ? <p className="success-banner">{message}</p> : null}
          {formError ? <p className="error-banner">{formError}</p> : null}
          <div className="hero-actions">
            <button className="primary-button" disabled={isSaving} type="submit">
              {isSaving ? "Saving..." : "Save account"}
            </button>
            <Link className="ghost-button" href="/dashboard/stripe">
              {stripeReady ? "Manage Stripe" : "Connect Stripe"}
            </Link>
          </div>
        </form>

        {/* Current-month snapshot (always this month) */}
        <section className="panel stack-md">
          <div>
            <p className="eyebrow">This month — {snapBroadcaster ? periodLabel(snapBroadcaster.period) : "—"}</p>
            <h2>Quick overview</h2>
          </div>

          {userDashboard.isLoadingDashboard ? (
            <p className="muted">Loading...</p>
          ) : (
            <>
              <div className="dashboard-stat-grid">
                <div className="dashboard-stat-card">
                  <span>Net earnings</span>
                  <strong>{formatCurrencyAmount(snapBroadcaster?.net_earnings_amount ?? 0, snapBroadcaster?.currency ?? "usd")}</strong>
                </div>
                <div className="dashboard-stat-card">
                  <span>Paid viewers</span>
                  <strong>{snapBroadcaster?.paid_viewer_count ?? 0}</strong>
                </div>
                <div className="dashboard-stat-card">
                  <span>Streams purchased</span>
                  <strong>{snapViewer?.streams_purchased ?? 0}</strong>
                </div>
                <div className="dashboard-stat-card">
                  <span>Total spent</span>
                  <strong>{formatCurrencyAmount(snapViewer?.total_spent_amount ?? 0, snapViewer?.currency ?? "usd")}</strong>
                </div>
                <div className="dashboard-stat-card">
                  <span>Streams owned</span>
                  <strong>{snapBroadcaster?.owned_stream_count ?? 0}</strong>
                </div>
                <div className="dashboard-stat-card">
                  <span>Stripe</span>
                  <strong>{stripeReady ? "ready" : "not connected"}</strong>
                </div>
              </div>

              {snapBroadcaster?.graph && (
                <div>
                  <p className="muted" style={{ fontSize: "0.8rem", marginBottom: "6px" }}>
                    Net earnings — {periodLabel(snapBroadcaster.period)} (daily)
                  </p>
                  <EarningsBarChart
                    labels={snapBroadcaster.graph.labels}
                    values={snapBroadcaster.graph.series.net_earnings}
                  />
                </div>
              )}
            </>
          )}
        </section>
      </div>

      {/* ── Period selector (controls everything below) ── */}
      <div className="panel" style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
        <strong>Filter by period</strong>
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(Number(e.target.value))}
          style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #d1d5db" }}
        >
          {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        <select
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(Number(e.target.value))}
          style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #d1d5db" }}
        >
          {MONTHS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
        </select>
        {!isCurrentPeriod && (
          <button
            className="ghost-button compact"
            onClick={() => { setSelectedYear(CURRENT_YEAR); setSelectedMonth(CURRENT_MONTH); }}
          >
            Back to this month
          </button>
        )}
        <span className="muted" style={{ fontSize: "0.875rem" }}>
          Showing: {selectedMonth > 0 ? MONTHS[selectedMonth]?.label + " " + selectedYear : "All of " + selectedYear}
        </span>
      </div>

      {/* ── Broadcaster earnings for selected period ── */}
      <section className="panel stack-md">
        <div>
          <p className="eyebrow">Broadcaster earnings</p>
          <h2>
            {selectedMonth > 0
              ? `${MONTHS[selectedMonth]?.label ?? ""} ${selectedYear}`
              : `Year ${selectedYear}`}
          </h2>
        </div>

        {isLoadingEarnings ? (
          <p className="muted">Loading earnings...</p>
        ) : earningsHistory ? (
          <>
            <div className="dashboard-stat-grid">
              <div className="dashboard-stat-card">
                <span>Net earnings</span>
                <strong>{formatCurrencyAmount(earningsHistory.summary.net_earnings_amount, earningsHistory.currency)}</strong>
              </div>
              <div className="dashboard-stat-card">
                <span>Gross sales</span>
                <strong>{formatCurrencyAmount(earningsHistory.summary.gross_sales_amount, earningsHistory.currency)}</strong>
              </div>
              <div className="dashboard-stat-card">
                <span>Platform fees</span>
                <strong>{formatCurrencyAmount(earningsHistory.summary.platform_fees_amount, earningsHistory.currency)}</strong>
              </div>
              <div className="dashboard-stat-card">
                <span>Payments</span>
                <strong>{earningsHistory.summary.successful_payment_count}</strong>
              </div>
              <div className="dashboard-stat-card">
                <span>Paid viewers</span>
                <strong>{earningsHistory.summary.paid_viewer_count}</strong>
              </div>
              <div className="dashboard-stat-card">
                <span>Refunded</span>
                <strong>{formatCurrencyAmount(earningsHistory.summary.refunded_amount, earningsHistory.currency)}</strong>
              </div>
            </div>

            <div>
              <p className="muted" style={{ fontSize: "0.8rem", marginBottom: "6px" }}>
                Net earnings — {earningsHistory.view === "daily" ? "daily breakdown" : "monthly breakdown"}
              </p>
              <EarningsBarChart
                labels={earningsHistory.graph.labels}
                values={earningsHistory.graph.series.net_earnings}
              />
            </div>

            {earningsHistory.summary.gross_sales_amount > earningsHistory.summary.net_earnings_amount && (
              <div>
                <p className="muted" style={{ fontSize: "0.8rem", marginBottom: "6px" }}>
                  Gross sales vs net earnings
                </p>
                <div style={{ display: "flex", gap: "8px" }}>
                  <div style={{ flex: 1 }}>
                    <p className="muted" style={{ fontSize: "0.75rem", marginBottom: "4px" }}>Gross</p>
                    <EarningsBarChart
                      labels={earningsHistory.graph.labels}
                      values={earningsHistory.graph.series.gross_sales}
                      color="#a5b4fc"
                      height={50}
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <p className="muted" style={{ fontSize: "0.75rem", marginBottom: "4px" }}>Net</p>
                    <EarningsBarChart
                      labels={earningsHistory.graph.labels}
                      values={earningsHistory.graph.series.net_earnings}
                      color="#6366f1"
                      height={50}
                    />
                  </div>
                  {earningsHistory.summary.refunded_amount > 0 && (
                    <div style={{ flex: 1 }}>
                      <p className="muted" style={{ fontSize: "0.75rem", marginBottom: "4px" }}>Refunds</p>
                      <EarningsBarChart
                        labels={earningsHistory.graph.labels}
                        values={earningsHistory.graph.series.refunds}
                        color="#ef4444"
                        height={50}
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {earningsHistory.breakdown.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>
                      <th style={{ padding: "6px 8px" }}>Period</th>
                      <th style={{ padding: "6px 8px" }}>Net</th>
                      <th style={{ padding: "6px 8px" }}>Gross</th>
                      <th style={{ padding: "6px 8px" }}>Payments</th>
                      <th style={{ padding: "6px 8px" }}>Refunded</th>
                    </tr>
                  </thead>
                  <tbody>
                    {earningsHistory.breakdown.map((row) => (
                      <tr key={row.period} style={{ borderBottom: "1px solid #f3f4f6" }}>
                        <td style={{ padding: "6px 8px" }}>{periodLabel(row.period)}</td>
                        <td style={{ padding: "6px 8px" }}>{formatCurrencyAmount(row.net_earnings_amount, earningsHistory.currency)}</td>
                        <td style={{ padding: "6px 8px" }}>{formatCurrencyAmount(row.gross_sales_amount, earningsHistory.currency)}</td>
                        <td style={{ padding: "6px 8px" }}>{row.successful_payment_count}</td>
                        <td style={{ padding: "6px 8px" }}>{formatCurrencyAmount(row.refunded_amount, earningsHistory.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : null}

        {/* Stream list filtered by selected period */}
        <div>
          <p className="eyebrow" style={{ marginBottom: "8px" }}>
            Streams in this period ({filteredStreams.length})
          </p>
          {filteredStreams.length === 0 ? (
            <p className="muted">No streams in this period.</p>
          ) : (
            <div className="stream-grid studio-owned-grid">
              {filteredStreams.map((stream) => (
                <LiveStreamCard key={stream.id} stream={stream} href={`/studio/${stream.id}`} ctaLabel="Open studio" />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── Viewer spend for selected period ── */}
      <section className="panel stack-md">
        <div>
          <p className="eyebrow">Viewer spend</p>
          <h2>
            {selectedMonth > 0
              ? `${MONTHS[selectedMonth]?.label ?? ""} ${selectedYear}`
              : `Year ${selectedYear}`}
          </h2>
        </div>

        {isLoadingSpend ? (
          <p className="muted">Loading spend...</p>
        ) : spendHistory ? (
          <>
            <div className="dashboard-stat-grid">
              <div className="dashboard-stat-card">
                <span>Total spent</span>
                <strong>{formatCurrencyAmount(spendHistory.summary.total_spent_amount, spendHistory.currency)}</strong>
              </div>
              <div className="dashboard-stat-card">
                <span>Streams purchased</span>
                <strong>{spendHistory.summary.streams_purchased}</strong>
              </div>
              <div className="dashboard-stat-card">
                <span>Refunded</span>
                <strong>{formatCurrencyAmount(spendHistory.summary.refunded_amount, spendHistory.currency)}</strong>
              </div>
            </div>

            <div>
              <p className="muted" style={{ fontSize: "0.8rem", marginBottom: "6px" }}>
                Total spent — {spendHistory.view === "daily" ? "daily breakdown" : "monthly breakdown"}
              </p>
              <EarningsBarChart
                labels={spendHistory.graph.labels}
                values={spendHistory.graph.series.total_spent}
                color="#10b981"
              />
            </div>

            {spendHistory.breakdown.length === 0 && (
              <p className="muted">No purchases in this period.</p>
            )}
          </>
        ) : null}

        {recentPurchases.length > 0 && (
          <>
            <p className="eyebrow" style={{ marginBottom: "4px" }}>Recent purchases (last 10)</p>
            <ul className="purchase-list">
              {recentPurchases.map((purchase) => (
                <li key={purchase.transaction_id}>
                  <div>
                    <strong>{purchase.stream_title}</strong>
                    <span>
                      Paid {formatCurrencyAmount(purchase.amount, purchase.currency)} on{" "}
                      {formatDateTime(purchase.paid_at ?? purchase.created_at)}
                    </span>
                  </div>
                  <Link className="ghost-button compact" href={`/watch/${purchase.stream_id}`}>
                    Open stream
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </section>
  );
}
