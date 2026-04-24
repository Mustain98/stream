export type User = {
  id: string;
  username: string;
  email: string | null;
  is_active: boolean;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type StreamSummary = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  broadcaster_id: string;
  started_at: string | null;
  viewer_count: number;
};

export type StreamRecord = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  broadcaster_id: string;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

export type StreamDetailsResponse = {
  stream: StreamRecord;
  viewer_count: number;
};

export type WsTicketResponse = {
  ticket: string;
  stream_id: string;
  role: "broadcaster" | "viewer";
};

export type ApiError = {
  detail?: string;
};
