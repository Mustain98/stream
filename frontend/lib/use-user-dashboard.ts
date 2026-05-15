"use client";

import { useCallback, useState } from "react";

import { api } from "./api";
import type { UserDashboardResponse } from "./types";

type Options = {
  token: string | null;
};

export function useUserDashboard({ token }: Options) {
  const [dashboard, setDashboard] = useState<UserDashboardResponse | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    if (!token) {
      return null;
    }

    try {
      setIsLoadingDashboard(true);
      setDashboardError(null);

      const response = await api.getDashboard(token);
      setDashboard(response);
      return response;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load account dashboard";

      setDashboardError(message);
      throw error;
    } finally {
      setIsLoadingDashboard(false);
    }
  }, [token]);

  return {
    dashboard,
    isLoadingDashboard,
    dashboardError,
    loadDashboard,
    setDashboard,
  };
}

