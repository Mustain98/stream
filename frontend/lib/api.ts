import type {
  ApiError,
  StreamDetailsResponse,
  StreamSummary,
  TokenResponse,
  User,
  WsTicketResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const WS_BASE_URL = API_BASE_URL.startsWith("https://")
  ? API_BASE_URL.replace("https://", "wss://")
  : API_BASE_URL.replace("http://", "ws://");

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
  getLiveStreams: () =>
    request<StreamSummary[]>("/stream/live", {
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
  createStream: (token: string, payload: { title: string; description: string }) =>
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
  getWsTicket: (token: string, streamId: string) =>
    request<WsTicketResponse>(`/ws-ticket/${streamId}`, {
      method: "POST",
      token,
    }),
};
