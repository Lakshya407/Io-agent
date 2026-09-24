/**
 * Rate limiting API — `GET /admin/rate-limits`, `GET /admin/rate-limits/stats`,
 * `POST`, `PATCH/DELETE /admin/rate-limits/{id}` (all admin-only).
 *
 * `/stats` is declared before `/{rule_id}` on the backend so the literal path
 * always wins.
 */

import { apiFetch } from "./client";
import type {
  RateLimitRule,
  RateLimitRuleCreate,
  RateLimitRuleUpdate,
  RateLimitStats,
} from "../types/rateLimit";

export const rateLimitsApi = {
  /** `GET /api/v1/admin/rate-limits/stats` — today's counters (UTC). */
  stats(): Promise<RateLimitStats> {
    return apiFetch<RateLimitStats>("/admin/rate-limits/stats");
  },

  /** `GET /api/v1/admin/rate-limits` — every configured rule. */
  list(): Promise<RateLimitRule[]> {
    return apiFetch<RateLimitRule[]>("/admin/rate-limits");
  },

  /** `POST /api/v1/admin/rate-limits` — takes effect next request (201). */
  create(payload: RateLimitRuleCreate): Promise<RateLimitRule> {
    return apiFetch<RateLimitRule>("/admin/rate-limits", {
      method: "POST",
      body: payload,
    });
  },

  /** `PATCH /api/v1/admin/rate-limits/{id}`. */
  update(
    ruleId: string,
    payload: RateLimitRuleUpdate,
  ): Promise<RateLimitRule> {
    return apiFetch<RateLimitRule>(`/admin/rate-limits/${ruleId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  /** `DELETE /api/v1/admin/rate-limits/{id}` — returns 204. */
  remove(ruleId: string): Promise<void> {
    return apiFetch<void>(`/admin/rate-limits/${ruleId}`, {
      method: "DELETE",
    });
  },
};
