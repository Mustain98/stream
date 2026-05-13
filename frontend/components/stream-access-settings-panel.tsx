"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import type {
  StreamAccessResponse,
  StreamAccessSettingsPayload,
  StripeConnectStatus,
} from "../lib/types";

type StreamAccessSettingsPanelProps = {
  access: StreamAccessResponse | null;
  isLoading: boolean;
  stripeStatus: StripeConnectStatus | null;
  isLoadingStripeStatus: boolean;
  onSave: (payload: StreamAccessSettingsPayload) => Promise<void>;
};

export function StreamAccessSettingsPanel({
  access,
  isLoading,
  stripeStatus,
  isLoadingStripeStatus,
  onSave,
}: StreamAccessSettingsPanelProps) {
  const [accessType, setAccessType] = useState<"free" | "paid">("free");
  const [priceAmount, setPriceAmount] = useState(0);
  const [currency, setCurrency] = useState("usd");
  const [freePreviewSeconds, setFreePreviewSeconds] = useState(0);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!access) {
      return;
    }

    setAccessType(access.access_type);
    setPriceAmount(access.price_amount);
    setCurrency(access.currency);
    setFreePreviewSeconds(access.free_preview_seconds);
  }, [access]);

  const stripeReady = Boolean(stripeStatus?.onboarding_completed);

  const paidBlockedByStripe = useMemo(() => {
    return accessType === "paid" && !stripeReady;
  }, [accessType, stripeReady]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (paidBlockedByStripe) {
      return;
    }

    setIsSaving(true);

    try {
      await onSave({
        access_type: accessType,
        price_amount: accessType === "paid" ? priceAmount : 0,
        currency,
        free_preview_seconds: accessType === "paid" ? freePreviewSeconds : 0,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="panel stack-md">
      <div>
        <p className="eyebrow">Access settings</p>
        <h2>Payment and preview</h2>
      </div>

      {isLoading ? <p className="muted">Loading access settings...</p> : null}

      {!isLoading ? (
        <form className="stack-md" onSubmit={handleSubmit}>
          <label className="field">
            <span>Access type</span>
            <select
              value={accessType}
              onChange={(event) =>
                setAccessType(event.target.value as "free" | "paid")
              }
            >
              <option value="free">Free</option>
              <option value="paid">Paid</option>
            </select>
          </label>

          {accessType === "paid" ? (
            <>
              {isLoadingStripeStatus ? (
                <p className="muted">Checking Stripe status...</p>
              ) : null}

              {!isLoadingStripeStatus && !stripeReady ? (
                <div className="error-surface panel stack-sm">
                  <p className="eyebrow">Stripe required</p>
                  <h3>Connect Stripe before making this stream paid.</h3>
                  <p className="muted">
                    Only broadcasters who want paid streams need Stripe. Free streams do
                    not require Stripe setup.
                  </p>

                  <Link className="primary-button compact" href="/dashboard/stripe">
                    Manage Stripe
                  </Link>
                </div>
              ) : null}

              <label className="field">
                <span>Price amount</span>
                <input
                  min={1}
                  type="number"
                  value={priceAmount}
                  onChange={(event) => setPriceAmount(Number(event.target.value))}
                />
                <small className="muted">
                  Amount is in the smallest currency unit. For USD, 100 means $1.00.
                </small>
              </label>

              <label className="field">
                <span>Currency</span>
                <input
                  value={currency}
                  onChange={(event) => setCurrency(event.target.value.toLowerCase())}
                />
              </label>

              <label className="field">
                <span>Free preview seconds</span>
                <input
                  min={0}
                  type="number"
                  value={freePreviewSeconds}
                  onChange={(event) =>
                    setFreePreviewSeconds(Number(event.target.value))
                  }
                />
              </label>
            </>
          ) : (
            <p className="muted">
              Viewers can watch the full stream without payment. Stripe is not required
              for free streams.
            </p>
          )}

          <button
            className="primary-button"
            disabled={isSaving || paidBlockedByStripe}
            type="submit"
          >
            {isSaving ? "Saving..." : "Save access settings"}
          </button>
        </form>
      ) : null}
    </div>
  );
}