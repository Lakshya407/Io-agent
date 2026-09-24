/**
 * Admin hooks — dashboard statistics, per-user usage, allowance updates and
 * the usage analytics endpoints (summary / by-user / by-model / timeline).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/admin";
import { queryKeys } from "../lib/queryClient";
import type { AllowanceUpdate, UsageFilterParams } from "../types/usage";
import type { PageParams } from "../types/common";

const DEFAULT_PAGE_SIZE = 20;

export function useAdminDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => adminApi.dashboard(),
  });
}

export function useAdminUsage(params: PageParams = {}) {
  const page = params.page ?? 1;
  const pageSize = params.page_size ?? DEFAULT_PAGE_SIZE;
  return useQuery({
    queryKey: queryKeys.adminUsage(page, pageSize),
    queryFn: () => adminApi.usage({ page, page_size: pageSize }),
  });
}

/** Platform totals (requests, tokens, active users) for a filtered period. */
export function useAdminUsageSummary(params: UsageFilterParams = {}) {
  return useQuery({
    queryKey: queryKeys.adminUsageSummary(params),
    queryFn: () => adminApi.usageSummary(params),
  });
}

/** Usage grouped by user (biggest consumers first). */
export function useAdminUsageUsers(params: UsageFilterParams = {}) {
  return useQuery({
    queryKey: queryKeys.adminUsageUsers(params),
    queryFn: () => adminApi.usageUsers(params),
  });
}

/** Usage grouped by model (biggest consumers first). */
export function useAdminUsageModels(params: UsageFilterParams = {}) {
  return useQuery({
    queryKey: queryKeys.adminUsageModels(params),
    queryFn: () => adminApi.usageModels(params),
  });
}

/** Usage over time, newest first (reverse before charting). */
export function useAdminUsageTimeline(params: UsageFilterParams = {}) {
  return useQuery({
    queryKey: queryKeys.adminUsageTimeline(params),
    queryFn: () => adminApi.usageTimeline(params),
  });
}

/**
 * One user's full allowance (including daily limits + enabled flag), used to
 * populate the allowance editor. Only fetched while a user is selected.
 */
export function useUsageForUser(userId: string | null) {
  return useQuery({
    queryKey: ["admin", "usage", "user", userId],
    queryFn: () => adminApi.usageForUser(userId as string),
    enabled: userId !== null,
  });
}

export function useUpdateAllowance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: string;
      payload: AllowanceUpdate;
    }) => adminApi.updateAllowance(userId, payload),
    onSuccess: () => {
      // Prefix invalidation: allowance rows, analytics and the personal views.
      queryClient.invalidateQueries({ queryKey: ["admin", "usage"] });
      queryClient.invalidateQueries({ queryKey: ["usage"] });
    },
  });
}
