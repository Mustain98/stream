"use client";

import Link from "next/link";
import { useEffect } from "react";

import { RequireAuth } from "../../../components/require-auth";
import { useSession } from "../../../components/session-provider";
import { useStripeConnect } from "../../../lib/use-stripe-connect";

export default function StripeDashboardPage() {
  return (
    <RequireAuth>
      <StripeDashboardContent />
    </RequireAuth>
  );
}

function StripeDashboardContent() {
  const { token, user } = useSession();

  const stripeConnect = useStripeConnect({
    token,
  });

  useEffect(() => {
    if (!token) {
      return;
    }

    void stripeConnect.loadStatus();
  }, [token, stripeConnect.loadStatus]);

  const handleStartOnboarding = async () => {
    if (!user?.email) {
      return;
    }

    try {
      const response = await stripeConnect.startOnboarding();

      if (response?.onboarding_url) {
        window.location.href = response.onboarding_url;
      }
    } catch {
      // Error is already stored in hook state.
    }
  };

  const status = stripeConnect.status;
  const isReady = Boolean(status?.onboarding_completed);
  const hasEmail = Boolean(user?.email);

  return (
    <section className="stack-xl">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Stripe Connect</p>
          <h1>Receive payments from paid live streams.</h1>
          <p className="muted hero-copy">
            Connect Stripe only if you want to create paid streams. Viewers do not need a
            connected Stripe account.
          </p>
        </div>

        <div className="stat-block">
          <span>Signed in as</span>
          <strong>{user?.username}</strong>
        </div>
      </div>

      {stripeConnect.stripeError ? (
        <p className="error-banner">{stripeConnect.stripeError}</p>
      ) : null}

      <div className="studio-grid">
        <section className="panel stack-md">
          <div>
            <p className="eyebrow">Account status</p>
            <h2>{isReady ? "Stripe is ready" : "Stripe setup required"}</h2>
          </div>

          {stripeConnect.isLoadingStatus ? (
            <p className="muted">Checking Stripe account status...</p>
          ) : null}

          {!stripeConnect.isLoadingStatus ? (
            <div className="meta-list">
              <StatusRow label="Connected" value={status?.connected} />
              <StatusRow label="Details submitted" value={status?.details_submitted} />
              <StatusRow label="Charges enabled" value={status?.charges_enabled} />
              <StatusRow label="Payouts enabled" value={status?.payouts_enabled} />
              <StatusRow
                label="Onboarding completed"
                value={status?.onboarding_completed}
              />

              <div>
                <span>Account ID</span>
                <strong>{status?.stripe_account_id || "—"}</strong>
              </div>

              <div>
                <span>Email</span>
                <strong>{user?.email || "Missing"}</strong>
              </div>
            </div>
          ) : null}
        </section>

        <section className="panel stack-md">
          <div>
            <p className="eyebrow">Monetization</p>
            <h2>{isReady ? "You can create paid streams" : "Connect Stripe"}</h2>
          </div>

          {isReady ? (
            <>
              <p className="muted">
                Your Stripe account is connected. You can now set stream access to paid
                from the studio room page.
              </p>

              <Link className="primary-button" href="/studio">
                Back to Studio
              </Link>
            </>
          ) : (
            <>
              <p className="muted">
                Stripe will collect the required payout and verification details. Your app
                only stores the connected account ID.
              </p>

              {!hasEmail ? (
                <div className="error-surface panel stack-sm">
                  <p className="eyebrow">Email required</p>
                  <h3>Add an email before connecting Stripe.</h3>
                  <p className="muted">
                    Stripe onboarding needs an email for the broadcaster account.
                  </p>

                  <Link className="primary-button compact" href="/profile">
                    Add email
                  </Link>
                </div>
              ) : null}

              <button
                className="primary-button"
                disabled={stripeConnect.isStartingOnboarding || !hasEmail}
                onClick={handleStartOnboarding}
                type="button"
              >
                {stripeConnect.isStartingOnboarding
                  ? "Opening Stripe..."
                  : status?.connected
                    ? "Continue Stripe onboarding"
                    : "Connect Stripe"}
              </button>

              <Link className="ghost-button compact" href="/studio">
                Back to Studio
              </Link>
            </>
          )}
        </section>
      </div>
    </section>
  );
}

function StatusRow({
  label,
  value,
}: {
  label: string;
  value: boolean | undefined;
}) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value ? "Yes" : "No"}</strong>
    </div>
  );
}