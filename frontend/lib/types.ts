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
  viewer_count?: number;
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
};

export type ViewerCountResponse = {
  stream_id: string;
  viewer_count: number;
};

export type SfuTicketResponse = {
  sfuUrl: string;
  token: string;
  streamId: string;
  roomId: string;
  role: "publisher" | "subscriber";
};

export type ApiError = {
  detail?: string;
};

export type ViewerInfo = {
  peerId: string;
  userId: string | null;
  username: string;
};

export type StreamState = "live" | "paused";

export type SfuMessage = {
  type:
    | "join"
    | "offer"
    | "answer"
    | "ice"
    | "leave"
    | "error"
    | "info"
    | "renegotiate"
    | "presence"
    | "stream-state"
    | "kicked"
    | string;

  sdp?: string;
  candidate?: RTCIceCandidateInit | null;
  message?: string;
  reason?: string;
  roomId?: string;
  viewerCount?: number;
  viewers?: ViewerInfo[];
  state?: StreamState;
};

export type BlockedUser = {
  id: string;
  stream_id: string;
  user_id: string;
  username: string;
  reason: string | null;
  created_at: string;
};

export type BlockedUsersResponse = {
  stream_id: string;
  blocked_users: BlockedUser[];
};

export type BlockViewerResponse = {
  status: string;
  stream_id: string;
  user_id: string;
  reason?: string | null;
  sfu?: unknown;
};