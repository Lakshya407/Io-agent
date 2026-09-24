/**
 * Usage types — mirror `app/schemas/usage.py`.
 */

/** `UsageOut` — allowance summary for a single user. */
export interface Usage {
  user_id: string;
  monthly_token_limit: number;
  monthly_request_limit: number;
  daily_token_limit: number | null;
  daily_request_limit: number | null;
  is_enabled: boolean;
  tokens_used: number;
  requests_used: number;
  tokens_remaining: number;
  requests_remaining: number;
  is_allowed: boolean;
  reset_at: string;
}

/** `UsageHistoryItem` — one aggregated row of usage history (per day). */
export interface UsageHistoryItem {
  period: string;
  requests: number;
  tokens: number;
}

/** `AllowanceUpdate` — payload for PATCH /api/v1/admin/users/{id}/allowance. */
export interface AllowanceUpdate {
  monthly_token_limit?: number | null;
  monthly_request_limit?: number | null;
  /** `null` clears the daily limit (unlimited). */
  daily_token_limit?: number | null;
  /** `null` clears the daily limit (unlimited). */
  daily_request_limit?: number | null;
  is_enabled?: boolean;
  reset_at?: string | null;
}

/** Query params for GET /api/v1/usage/history. */
export interface UsageHistoryParams {
  model?: string;
  provider?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

/** `UsageMeOut` — GET /api/v1/usage/me (own data only). */
export interface UsageMe {
  tokens_today: number;
  requests_today: number;
  tokens_remaining_today: number | null;
  requests_remaining_today: number | null;
  tokens_this_month: number;
  requests_this_month: number;
  tokens_remaining: number;
  requests_remaining: number;
  monthly_token_limit: number;
  monthly_request_limit: number;
  daily_token_limit: number | null;
  daily_request_limit: number | null;
  is_enabled: boolean;
  is_allowed: boolean;
  reset_at: string;
  current_model: string | null;
}

/** `UsageSummaryOut` — GET /api/v1/usage/summary (compact personal view). */
export interface UsageSummary {
  tokens_today: number;
  requests_today: number;
  tokens_this_month: number;
  requests_this_month: number;
  tokens_remaining: number;
  requests_remaining: number;
  current_model: string | null;
}

/**
 * Shared query params for the admin usage analytics endpoints.
 *
 * Mirrors the annotated params in `app/api/admin.py`; explicit `date_from` /
 * `date_to` always win over `range` on the backend.
 */
export interface UsageFilterParams {
  /** Preset window: today | 7d | 30d | all. */
  range?: string;
  /** ISO datetime; inclusive custom-range start. */
  date_from?: string;
  /** ISO datetime; inclusive custom-range end. */
  date_to?: string;
  /** Model display name as recorded in usage_records. */
  model?: string;
  /** Restrict to a single user. */
  user_id?: string;
}

/** `AdminUsageSummary` — GET /api/v1/admin/usage/summary. */
export interface AdminUsageSummary {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  cancelled_requests: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  active_users: number;
  average_response_time_ms: number | null;
}

/** `AdminModelUsageRow` — GET /api/v1/admin/usage/models. */
export interface AdminModelUsageRow {
  model: string;
  provider: string | null;
  requests: number;
  successful_requests: number;
  failed_requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  average_response_time_ms: number | null;
}

/** `AdminUserUsageRow` — GET /api/v1/admin/usage/users. */
export interface AdminUserUsageRow {
  user_id: string;
  email: string;
  name: string;
  requests: number;
  successful_requests: number;
  failed_requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  average_response_time_ms: number | null;
}

/** `UsageTimelinePoint` — GET /api/v1/admin/usage/timeline (newest first). */
export interface UsageTimelinePoint {
  period: string;
  requests: number;
  failed_requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  average_response_time_ms: number | null;
}
