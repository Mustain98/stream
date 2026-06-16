import type {
  ApiError,
  BlockedUsersResponse,
  BlockViewerResponse,
  CheckoutResponse,
  EarningsHistoryResponse,
  SfuTicketResponse,
  SpendHistoryResponse,
  StreamAccessResponse,
  StreamAccessSettingsPayload,
  StreamDetailsResponse,
  StreamEarningsSummary,
  StreamSummary,
  StripeConnectStatus,
  StripeOnboardingResponse,
  TokenResponse,
  User,
  UserDashboardResponse,
  ViewerCountResponse,
  UserUpdatePayload
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & {
  token?: string | null;
  body?: unknown;
};

export class HttpError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    let message = "Request failed";

    try {
      const errorBody = (await response.json()) as ApiError;

      if (typeof errorBody.detail === "string") {
        message = errorBody.detail;
      }
    } catch {
      message = response.statusText || message;
    }

    throw new HttpError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export const api = {
  signup: (username: string, password: string) =>
    request<TokenResponse>("/auth/signup", {
      method: "POST",
      body: { username, password },
    }),

  login: (username: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: { username, password },
    }),

  me: (token: string) =>
    request<User>("/auth/me", {
      token,
      cache: "no-store",
    }),

  getDashboard: (token: string) =>
    request<UserDashboardResponse>("/auth/dashboard", {
      token,
      cache: "no-store",
    }),

  getLiveStreams: () =>
    request<StreamSummary[]>("/stream/live", {
      cache: "no-store",
    }),

  getUpcomingStreams: () =>
    request<StreamSummary[]>("/stream/upcoming", {
      cache: "no-store",
    }),

  getOwnedStreams: (token: string) =>
    request<StreamSummary[]>("/stream/owned", {
      token,
      cache: "no-store",
    }),

  getStream: (streamId: string) =>
    request<StreamDetailsResponse>(`/stream/${streamId}`, {
      cache: "no-store",
    }),

  getStreamEarnings: (token: string, streamId: string) =>
    request<StreamEarningsSummary>(`/stream/${streamId}/earnings`, {
      token,
      cache: "no-store",
    }),

  getViewerCount: (token: string, streamId: string) =>
    request<ViewerCountResponse>(`/stream/${streamId}/viewers`, {
      token,
      cache: "no-store",
    }),

  createStream: (token: string, payload: { title: string; description: string; min_duration_seconds: number; scheduled_start_time?: string; scheduled_end_time?: string }) =>
    request<StreamDetailsResponse["stream"]>("/stream/create", {
      method: "POST",
      token,
      body: payload,
    }),

  startStream: (token: string, streamId: string) =>
    request<StreamDetailsResponse["stream"]>(`/stream/start/${streamId}`, {
      method: "POST",
      token,
    }),

  endStream: (token: string, streamId: string) =>
    request<StreamDetailsResponse["stream"]>(`/stream/end/${streamId}`, {
      method: "POST",
      token,
    }),

  joinStream: (token: string, streamId: string) =>
    request(`/stream/join/${streamId}`, {
      method: "POST",
      token,
    }),

  leaveStream: (token: string, streamId: string) =>
    request(`/stream/leave/${streamId}`, {
      method: "POST",
      token,
    }),

  getSfuTicket: (token: string, streamId: string) =>
    request<SfuTicketResponse>(`/sfu/ticket/${streamId}`, {
      method: "POST",
      token,
    }),

  blockViewer: (token: string, streamId: string, userId: string, reason = "blocked") =>
    request<BlockViewerResponse>(`/stream/${streamId}/block/${userId}`, {
      method: "POST",
      token,
      body: { reason },
    }),

  unblockViewer: (token: string, streamId: string, userId: string) =>
    request<BlockViewerResponse>(`/stream/${streamId}/block/${userId}`, {
      method: "DELETE",
      token,
    }),

  getBlockedUsers: (token: string, streamId: string) =>
    request<BlockedUsersResponse>(`/stream/${streamId}/blocked-users`, {
      token,
      cache: "no-store",
    }),

  getStreamAccess: (token: string, streamId: string) =>
    request<StreamAccessResponse>(`/stream/${streamId}/access`, {
      token,
      cache: "no-store",
    }),

  updateStreamAccessSettings: (
    token: string,
    streamId: string,
    payload: StreamAccessSettingsPayload
  ) =>
    request<StreamAccessResponse>(`/stream/${streamId}/access-settings`, {
      method: "PATCH",
      token,
      body: payload,
    }),

  createCheckoutSession: (token: string, streamId: string) =>
    request<CheckoutResponse>(`/stream/${streamId}/checkout`, {
      method: "POST",
      token,
    }),

  getStripeConnectStatus: (token: string) =>
    request<StripeConnectStatus>("/stripe/connect/status", {
      token,
      cache: "no-store",
    }),

  createStripeOnboarding: (token: string) =>
    request<StripeOnboardingResponse>("/stripe/connect/onboard", {
      method: "POST",
      token,
    }),
  updateMe: (token: string, payload: UserUpdatePayload) =>
    request<User>("/auth/me", {
      method: "PATCH",
      token,
      body: payload,
    }),

  getEarningsHistory: (token: string, year?: number, month?: number) => {
    const params = new URLSearchParams();
    if (year) params.set("year", String(year));
    if (month) params.set("month", String(month));
    const qs = params.size ? `?${params.toString()}` : "";
    return request<EarningsHistoryResponse>(`/auth/earnings/history${qs}`, {
      token,
      cache: "no-store",
    });
  },

  getSpendHistory: (token: string, year?: number, month?: number) => {
    const params = new URLSearchParams();
    if (year) params.set("year", String(year));
    if (month) params.set("month", String(month));
    const qs = params.size ? `?${params.toString()}` : "";
    return request<SpendHistoryResponse>(`/auth/spend/history${qs}`, {
      token,
      cache: "no-store",
    });
  },
};
