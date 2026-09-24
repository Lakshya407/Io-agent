/**
 * Admin API — `GET /admin/dashboard`, `GET /admin/usage`,
 * `GET /admin/usage/{id}`, `PATCH /admin/users/{id}/allowance` and the
 * usage analytics endpoints (`/admin/usage/summary|users|models|timeline`).
 */

import { apiFetch } from "./client";
import type { PaginatedResponse, PageParams } from "../types/common";
import type { AdminUsageRow, DashboardStats } from "../types/admin";
import type {
  AdminModelUsageRow,
  AdminUsageSummary,
  AdminUserUsageRow,
  AllowanceUpdate,
  Usage,
  UsageFilterParams,
  UsageTimelinePoint,
} from "../types/usage";

export const adminApi = {
  /** `GET /api/v1/admin/dashboard` — platform statistics. */
  dashboard(): Promise<DashboardStats> {
    return apiFetch<DashboardStats>("/admin/dashboard");
  },

  /** `GET /api/v1/admin/usage` — usage for all users. */
  usage(params: PageParams = {}): Promise<PaginatedResponse<AdminUsageRow>> {
    return apiFetch<PaginatedResponse<AdminUsageRow>>("/admin/usage", {
      params,
    });
  },

  /** `GET /api/v1/admin/usage/{user_id}`. */
  usageForUser(userId: string): Promise<Usage> {
    return apiFetch<Usage>(`/admin/usage/${userId}`);
  },

  /** `PATCH /api/v1/admin/users/{user_id}/allowance`. */
  updateAllowance(userId: string, payload: AllowanceUpdate): Promise<Usage> {
    return apiFetch<Usage>(`/admin/users/${userId}/allowance`, {
      method: "PATCH",
      body: payload,
    });
  },

  /** `GET /api/v1/admin/usage/summary` — platform totals for the period. */
  usageSummary(params: UsageFilterParams = {}): Promise<AdminUsageSummary> {
    return apiFetch<AdminUsageSummary>("/admin/usage/summary", { params });
  },

  /** `GET /api/v1/admin/usage/users` — usage grouped by user (admin). */
  usageUsers(params: UsageFilterParams = {}): Promise<AdminUserUsageRow[]> {
    return apiFetch<AdminUserUsageRow[]>("/admin/usage/users", { params });
  },

  /** `GET /api/v1/admin/usage/models` — usage grouped by model (admin). */
  usageModels(params: UsageFilterParams = {}): Promise<AdminModelUsageRow[]> {
    return apiFetch<AdminModelUsageRow[]>("/admin/usage/models", { params });
  },

  /** `GET /api/v1/admin/usage/timeline` — usage over time (admin). */
  usageTimeline(
    params: UsageFilterParams = {},
  ): Promise<UsageTimelinePoint[]> {
    return apiFetch<UsageTimelinePoint[]>("/admin/usage/timeline", { params });
  },
};
