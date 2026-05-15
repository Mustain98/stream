"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { LiveStreamCard } from "../../components/live-stream-card";
import { RequireAuth } from "../../components/require-auth";
import { useSession } from "../../components/session-provider";
import { api } from "../../lib/api";
import { formatCurrencyAmount } from "../../lib/money";
import { useUserDashboard } from "../../lib/use-user-dashboard";

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString();
}

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfileContent />
    </RequireAuth>
  );
}

function ProfileContent() {
  const { token, user, refreshUser } = useSession();
  const userDashboard = useUserDashboard({
    token,
  });

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUsername(user?.username || "");
    setEmail(user?.email || "");
  }, [user?.username, user?.email]);

  useEffect(() => {
    if (!token) {
      return;
    }

    void userDashboard.loadDashboard();
  }, [token, userDashboard.loadDashboard]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!token) {
      return;
    }

    setIsSaving(true);
    setMessage(null);
    setError(null);

    try {
      await api.updateMe(token, {
        username: username.trim(),
        email: email.trim() || null,
      });

      await refreshUser();
      await userDashboard.loadDashboard();

      setMessage("Account details updated.");
    } catch (updateError) {
      const errorMessage =
        updateError instanceof Error ? updateError.message : "Failed to update account";

      setError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const dashboard = userDashboard.dashboard;
  const broadcasterStats = dashboard?.broadcaster_stats;
  const viewerStats = dashboard?.viewer_stats;
  const stripeStatus = dashboard?.stripe_status;
  const stripeReady = Boolean(stripeStatus?.onboarding_completed);
  const ownedStreams = dashboard?.owned_streams ?? [];
  const recentPurchases = dashboard?.recent_purchases ?? [];

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Account dashboard</p>
          <h1>See your profile, streams, and payments in one place.</h1>
          <p className="muted hero-copy">
            Keep your profile current, watch your paid-stream earnings, and review
            the streams you have purchased.
          </p>
        </div>

        <div className="stat-block">
          <span>Signed in as</span>
          <strong>{user?.username}</strong>
        </div>
      </div>

      {userDashboard.dashboardError ? (
        <p className="error-banner">{userDashboard.dashboardError}</p>
      ) : null}

      <div className="studio-grid">
        <form className="panel stack-md" onSubmit={handleSubmit}>
          <div>
            <p className="eyebrow">Profile</p>
            <h2>Account details</h2>
          </div>

          <label className="field">
            <span>Username</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Your username"
              required
            />
          </label>

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              placeholder="you@example.com"
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>

          <div className="meta-list">
            <div>
              <span>User ID</span>
              <strong>{user?.id || "—"}</strong>
            </div>

            <div>
              <span>Joined</span>
              <strong>{formatDateTime(user?.created_at)}</strong>
            </div>

            <div>
              <span>Status</span>
              <strong>{user?.is_active ? "active" : "inactive"}</strong>
            </div>
          </div>

          {message ? <p className="success-banner">{message}</p> : null}
          {error ? <p className="error-banner">{error}</p> : null}

          <div className="hero-actions">
            <button className="primary-button" disabled={isSaving} type="submit">
              {isSaving ? "Saving..." : "Save account"}
            </button>

            <Link className="ghost-button" href="/dashboard/stripe">
              {stripeReady ? "Manage Stripe" : "Connect Stripe"}
            </Link>
          </div>
        </form>

        <section className="panel stack-md">
          <div>
            <p className="eyebrow">Overview</p>
            <h2>Your activity at a glance</h2>
          </div>

          {userDashboard.isLoadingDashboard ? (
            <p className="muted">Loading account summary...</p>
          ) : null}

          {!userDashboard.isLoadingDashboard ? (
            <div className="dashboard-stat-grid">
              <div className="dashboard-stat-card">
                <span>Net earnings</span>
                <strong>
                  {formatCurrencyAmount(
                    broadcasterStats?.net_earnings_amount ?? 0,
                    broadcasterStats?.currency ?? "usd"
                  )}
                </strong>
              </div>

              <div className="dashboard-stat-card">
                <span>Gross sales</span>
                <strong>
                  {formatCurrencyAmount(
                    broadcasterStats?.gross_sales_amount ?? 0,
                    broadcasterStats?.currency ?? "usd"
                  )}
                </strong>
              </div>

              <div className="dashboard-stat-card">
                <span>Paid viewers</span>
                <strong>{broadcasterStats?.paid_viewer_count ?? 0}</strong>
              </div>

              <div className="dashboard-stat-card">
                <span>Purchased streams</span>
                <strong>{viewerStats?.purchased_stream_count ?? 0}</strong>
              </div>

              <div className="dashboard-stat-card">
                <span>Total spent</span>
                <strong>
                  {formatCurrencyAmount(
                    viewerStats?.total_spent_amount ?? 0,
                    viewerStats?.currency ?? "usd"
                  )}
                </strong>
              </div>

              <div className="dashboard-stat-card">
                <span>Stripe</span>
                <strong>{stripeReady ? "ready" : "not connected"}</strong>
              </div>
            </div>
          ) : null}
        </section>
      </div>

      <section className="panel stack-md">
        <div>
          <p className="eyebrow">Broadcaster summary</p>
          <h2>Your streams and earnings</h2>
        </div>

        <div className="meta-list">
          <div>
            <span>Owned streams</span>
            <strong>{broadcasterStats?.owned_stream_count ?? 0}</strong>
          </div>

          <div>
            <span>Live now</span>
            <strong>{broadcasterStats?.live_stream_count ?? 0}</strong>
          </div>

          <div>
            <span>Ended streams</span>
            <strong>{broadcasterStats?.ended_stream_count ?? 0}</strong>
          </div>

          <div>
            <span>Unique viewers</span>
            <strong>{broadcasterStats?.total_unique_viewers ?? 0}</strong>
          </div>

          <div>
            <span>Refunded</span>
            <strong>
              {formatCurrencyAmount(
                broadcasterStats?.refunded_amount ?? 0,
                broadcasterStats?.currency ?? "usd"
              )}
            </strong>
          </div>

          <div>
            <span>Refund pending</span>
            <strong>
              {formatCurrencyAmount(
                broadcasterStats?.refund_pending_amount ?? 0,
                broadcasterStats?.currency ?? "usd"
              )}
            </strong>
          </div>
        </div>

        {ownedStreams.length === 0 ? (
          <p className="muted">You have not created any streams yet.</p>
        ) : (
          <div className="stream-grid studio-owned-grid">
            {ownedStreams.map((stream) => (
              <LiveStreamCard
                key={stream.id}
                stream={stream}
                href={`/studio/${stream.id}`}
                ctaLabel="Open studio"
              />
            ))}
          </div>
        )}
      </section>

      <section className="panel stack-md">
        <div>
          <p className="eyebrow">Viewer summary</p>
          <h2>Streams you have paid for</h2>
        </div>

        <div className="meta-list">
          <div>
            <span>Successful payments</span>
            <strong>{viewerStats?.successful_payment_count ?? 0}</strong>
          </div>

          <div>
            <span>Refunded spend</span>
            <strong>
              {formatCurrencyAmount(
                viewerStats?.refunded_spend_amount ?? 0,
                viewerStats?.currency ?? "usd"
              )}
            </strong>
          </div>
        </div>

        {recentPurchases.length === 0 ? (
          <p className="muted">You have not purchased access to any paid streams yet.</p>
        ) : (
          <ul className="purchase-list">
            {recentPurchases.map((purchase) => (
              <li key={purchase.transaction_id}>
                <div>
                  <strong>{purchase.stream_title}</strong>
                  <span>
                    Paid {formatCurrencyAmount(purchase.amount, purchase.currency)} on{" "}
                    {formatDateTime(purchase.paid_at || purchase.created_at)}
                  </span>
                </div>

                <Link className="ghost-button compact" href={`/watch/${purchase.stream_id}`}>
                  Open stream
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

