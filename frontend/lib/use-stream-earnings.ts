"use client";

import { useCallback, useState } from "react";

import { api } from "./api";
import type { StreamEarningsSummary } from "./types";

type Options = {
  token: string | null;
  streamId: string;
};

export function useStreamEarnings({ token, streamId }: Options) {
  const [earnings, setEarnings] = useState<StreamEarningsSummary | null>(null);
  const [isLoadingEarnings, setIsLoadingEarnings] = useState(false);
  const [earningsError, setEarningsError] = useState<string | null>(null);

  const loadEarnings = useCallback(async () => {
    if (!token) {
      return null;
    }

    try {
      setIsLoadingEarnings(true);
      setEarningsError(null);

      const response = await api.getStreamEarnings(token, streamId);
      setEarnings(response);
      return response;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load stream earnings";

      setEarningsError(message);
      throw error;
    } finally {
      setIsLoadingEarnings(false);
    }
  }, [streamId, token]);

  return {
    earnings,
    isLoadingEarnings,
    earningsError,
    loadEarnings,
    setEarnings,
  };
}

