/**
 * Usage types — mirror `app/schemas/usage.py`.
 */

/** `UsageOut` — allowance summary for a single user. */
export interface Usage {
  user_id: string;
  monthly_token_limit: number;
  monthly_request_limit: number;
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
