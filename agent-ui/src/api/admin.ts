/**
 * Admin API — `GET /admin/dashboard`, `GET /admin/usage`,
 * `GET /admin/usage/{id}`, `PATCH /admin/users/{id}/allowance`.
 */

import { apiFetch } from "./client";
import type { PaginatedResponse, PageParams } from "../types/common";
import type {
  AdminUsageRow,
  DashboardStats,
} from "../types/admin";
import type { AllowanceUpdate } from "../types/usage";
import type { Usage } from "../types/usage";

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
  updateAllowance(
    userId: string,
    payload: AllowanceUpdate,
  ): Promise<Usage> {
    return apiFetch<Usage>(`/admin/users/${userId}/allowance`, {
      method: "PATCH",
      body: payload,
    });
  },
};
