/**
 * Admin hooks — dashboard statistics, per-user usage and allowance updates.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/admin";
import { queryKeys } from "../lib/queryClient";
import type { AllowanceUpdate } from "../types/usage";
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
      queryClient.invalidateQueries({ queryKey: ["admin", "usage"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.usage });
    },
  });
}
