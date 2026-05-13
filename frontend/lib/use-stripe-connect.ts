"use client";

import { useCallback, useState } from "react";

import { api } from "./api";
import type { StripeConnectStatus } from "./types";

type UseStripeConnectOptions = {
  token: string | null;
};

export function useStripeConnect({ token }: UseStripeConnectOptions) {
  const [status, setStatus] = useState<StripeConnectStatus | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);
  const [isStartingOnboarding, setIsStartingOnboarding] = useState(false);
  const [stripeError, setStripeError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    if (!token) {
      return null;
    }

    try {
      setIsLoadingStatus(true);
      setStripeError(null);

      const response = await api.getStripeConnectStatus(token);
      setStatus(response);

      return response;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load Stripe status";

      setStripeError(message);
      throw error;
    } finally {
      setIsLoadingStatus(false);
    }
  }, [token]);

  const startOnboarding = useCallback(async () => {
    if (!token) {
      return null;
    }

    try {
      setIsStartingOnboarding(true);
      setStripeError(null);

      const response = await api.createStripeOnboarding(token);
      return response;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to start Stripe onboarding";

      setStripeError(message);
      throw error;
    } finally {
      setIsStartingOnboarding(false);
    }
  }, [token]);

  return {
    status,
    setStatus,
    isLoadingStatus,
    isStartingOnboarding,
    stripeError,
    loadStatus,
    startOnboarding,
  };
}