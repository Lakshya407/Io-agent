/**
 * Rate limiting types — mirror `app/schemas/rate_limit.py`.
 */

export type RateLimitScope = "all" | "user" | "ip";

/** `RateLimitRuleOut` — one admin-managed rate limit rule. */
export interface RateLimitRule {
  id: string;
  scope: RateLimitScope;
  /** Requests allowed within `window_seconds`. */
  limit: number;
  window_seconds: number;
  action: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** `RateLimitRuleCreate` — payload for POST /api/v1/admin/rate-limits. */
export interface RateLimitRuleCreate {
  scope?: RateLimitScope;
  limit: number;
  window_seconds: number;
  action?: "block";
  is_active?: boolean;
}

/** `RateLimitRuleUpdate` — payload for PATCH /api/v1/admin/rate-limits/{id}. */
export interface RateLimitRuleUpdate {
  scope?: RateLimitScope;
  limit?: number;
  window_seconds?: number;
  action?: "block";
  is_active?: boolean;
}

/** `RateLimitStatsOut` — today's counters (best-effort, Redis-backed). */
export interface RateLimitStats {
  date: string;
  checked: number;
  blocked: number;
  violations: number;
}
