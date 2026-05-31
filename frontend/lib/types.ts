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
  broadcaster_username?: string | null;
  started_at: string | null;
  scheduled_start_time?: string | null;
  scheduled_end_time?: string | null;
  viewer_count?: number;
  earnings_summary?: StreamEarningsSummary | null;
};

export type StreamRecord = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  broadcaster_id: string;
  started_at: string | null;
  ended_at: string | null;
  scheduled_start_time?: string | null;
  scheduled_end_time?: string | null;
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
  accessMode?: "free" | "paid" | "preview";
  previewSeconds?: number;
};

export type ApiError = {
  detail?: string;
};

export type ViewerInfo = {
  peerId: string;
  userId: string | null;
  username: string;
};

export type ChatRole = "publisher" | "subscriber";

export type ChatMentionUser = {
  peerId: string;
  userId: string | null;
  username: string;
  role?: ChatRole | string;
};

export type StreamChatMessage = {
  id: string;
  roomId?: string;
  peerId: string;
  userId: string | null;
  username: string;
  role?: ChatRole | string;
  message: string;
  mentions: ChatMentionUser[];
  receivedAt: string;
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
    | "payment-required"
    | "chat"
    | "earnings-update"
    | string;

  sdp?: string;
  candidate?: RTCIceCandidateInit | null;
  message?: string;
  reason?: string;
  roomId?: string;
  streamId?: string;
  viewerCount?: number;
  viewers?: ViewerInfo[];
  state?: StreamState;
  peerId?: string;
  userId?: string | null;
  username?: string;
  role?: ChatRole | string;
  mentions?: ChatMentionUser[];
  summary?: StreamEarningsSummary;
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

export type StreamAccessResponse = {
  stream_id: string;
  access_type: "free" | "paid";
  price_amount: number;
  currency: string;
  free_preview_seconds: number;
  has_paid: boolean;
  can_watch: boolean;
  access_mode: "free" | "preview" | "paid" | "payment_required";
};

export type StreamEarningsSummary = {
  stream_id: string;
  currency: string;
  price_amount: number;
  access_type: "free" | "paid";
  viewer_count: number;
  successful_payment_count: number;
  paid_viewer_count: number;
  gross_sales_amount: number;
  platform_fees_amount: number;
  net_earnings_amount: number;
  refunded_amount: number;
  refund_pending_amount: number;
  refunded_payment_count: number;
  refund_pending_count: number;
  last_payment_at: string | null;
  updated_at: string;
};

export type BroadcasterDashboardStats = {
  owned_stream_count: number;
  live_stream_count: number;
  ended_stream_count: number;
  total_unique_viewers: number;
  successful_payment_count: number;
  paid_viewer_count: number;
  gross_sales_amount: number;
  platform_fees_amount: number;
  net_earnings_amount: number;
  refunded_amount: number;
  refund_pending_amount: number;
  refunded_payment_count: number;
  refund_pending_count: number;
  currency: string;
};

export type ViewerDashboardStats = {
  successful_payment_count: number;
  purchased_stream_count: number;
  total_spent_amount: number;
  refunded_spend_amount: number;
  currency: string;
};

export type DashboardPurchase = {
  transaction_id: string;
  stream_id: string;
  stream_title: string;
  broadcaster_id: string;
  amount: number;
  currency: string;
  status: string;
  paid_at: string | null;
  created_at: string;
};

export type UserDashboardResponse = {
  user: User;
  stripe_status: StripeConnectStatus | null;
  broadcaster_stats: BroadcasterDashboardStats;
  viewer_stats: ViewerDashboardStats;
  owned_streams: StreamSummary[];
  recent_purchases: DashboardPurchase[];
};

export type StreamAccessSettingsPayload = {
  access_type: "free" | "paid";
  price_amount: number;
  currency: string;
  free_preview_seconds: number;
};

export type CheckoutResponse = {
  checkout_url?: string;
  checkout_session_id?: string;
  transaction_id?: string;
  status?: string;
  stream_id?: string;
  amount?: number;
  currency?: string;
  platform_fee_amount?: number;
  broadcaster_amount?: number;
  broadcaster_id?: string;
};

export type StripeConnectStatus = {
  connected: boolean;
  stripe_account_id: string | null;
  details_submitted: boolean;
  charges_enabled: boolean;
  payouts_enabled: boolean;
  onboarding_completed: boolean;
};

export type StripeOnboardingResponse = {
  onboarding_url: string;
  stripe_account_id: string;
  onboarding_completed: boolean;
};

export type UserUpdatePayload = {
  username?: string;
  email?: string | null;
};
