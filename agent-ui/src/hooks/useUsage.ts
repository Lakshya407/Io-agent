/**
 * Usage hooks — the current user's allowance and aggregated history.
 */

import { useQuery } from "@tanstack/react-query";
import { usageApi } from "../api/usage";
import { queryKeys } from "../lib/queryClient";
import type { UsageHistoryParams } from "../types/usage";

export function useUsage() {
  return useQuery({
    queryKey: queryKeys.usage,
    queryFn: () => usageApi.current(),
  });
}

export function useUsageHistory(params: UsageHistoryParams = {}) {
  return useQuery({
    queryKey: queryKeys.usageHistory(params),
    queryFn: () => usageApi.history(params),
  });
}
