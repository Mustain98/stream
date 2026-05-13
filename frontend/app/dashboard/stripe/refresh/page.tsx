"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { RequireAuth } from "../../../../components/require-auth";

export default function StripeRefreshPage() {
  return (
    <RequireAuth>
      <StripeRefreshContent />
    </RequireAuth>
  );
}

function StripeRefreshContent() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard/stripe");
  }, [router]);

  return (
    <section className="stack-xl">
      <div className="center-card">
        <p className="eyebrow">Stripe Connect</p>
        <h1>Refreshing onboarding link...</h1>
        <p className="muted">Redirecting you back to Stripe setup.</p>
      </div>
    </section>
  );
}