"use client";

import { useCallback, useState } from "react";

import { api } from "./api";
import type {
  StreamAccessResponse,
  StreamAccessSettingsPayload,
} from "./types";

type UseStreamAccessOptions = {
  token: string | null;
  streamId: string;
};

export function useStreamAccess({ token, streamId }: UseStreamAccessOptions) {
  const [access, setAccess] = useState<StreamAccessResponse | null>(null);
  const [isLoadingAccess, setIsLoadingAccess] = useState(false);
  const [accessError, setAccessError] = useState<string | null>(null);

  const loadAccess = useCallback(async () => {
    if (!token) {
      return null;
    }

    try {
      setIsLoadingAccess(true);
      setAccessError(null);

      const response = await api.getStreamAccess(token, streamId);
      setAccess(response);

      return response;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load stream access";

      setAccessError(message);
      throw error;
    } finally {
      setIsLoadingAccess(false);
    }
  }, [streamId, token]);

  const updateAccess = useCallback(
    async (payload: StreamAccessSettingsPayload) => {
      if (!token) {
        return;
      }

      try {
        setAccessError(null);

        const response = await api.updateStreamAccessSettings(
          token,
          streamId,
          payload
        );

        setAccess(response);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to update access settings";

        setAccessError(message);
        throw error;
      }
    },
    [streamId, token]
  );

  const createCheckout = useCallback(async () => {
    if (!token) {
      return null;
    }

    try {
      setAccessError(null);

      return await api.createCheckoutSession(token, streamId);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to start checkout";

      setAccessError(message);
      throw error;
    }
  }, [streamId, token]);

  return {
    access,
    isLoadingAccess,
    accessError,
    loadAccess,
    updateAccess,
    createCheckout,
  };
}