"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "../../../../components/require-auth";
import { useSession } from "../../../../components/session-provider";
import { useStripeConnect } from "../../../../lib/use-stripe-connect";

export default function StripeReturnPage() {
  return (
    <RequireAuth>
      <StripeReturnContent />
    </RequireAuth>
  );
}

function StripeReturnContent() {
  const { token } = useSession();

  const stripeConnect = useStripeConnect({
    token,
  });

  const [message, setMessage] = useState("Checking Stripe onboarding status...");

  useEffect(() => {
    if (!token) {
      return;
    }

    const checkStatus = async () => {
      try {
        const status = await stripeConnect.loadStatus();

        if (status?.onboarding_completed) {
          setMessage("Stripe setup completed. You can now create paid live streams.");
          return;
        }

        setMessage("Stripe onboarding is not complete yet. Continue setup to receive payments.");
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Failed to check Stripe status";

        setMessage(errorMessage);
      }
    };

    void checkStatus();
  }, [token, stripeConnect.loadStatus]);

  const isComplete = Boolean(stripeConnect.status?.onboarding_completed);

  return (
    <section className="stack-xl">
      <div className="center-card">
        <p className="eyebrow">Stripe Connect</p>
        <h1>{isComplete ? "Stripe connected" : "Stripe setup incomplete"}</h1>
        <p className="muted">{message}</p>

        <div className="hero-actions">
          {isComplete ? (
            <Link className="primary-button" href="/studio">
              Go to Studio
            </Link>
          ) : (
            <Link className="primary-button" href="/dashboard/stripe">
              Continue Stripe setup
            </Link>
          )}

          <Link className="ghost-button" href="/">
            Home
          </Link>
        </div>
      </div>
    </section>
  );
}