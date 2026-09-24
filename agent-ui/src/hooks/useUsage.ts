/**
 * Usage hooks — the current user's allowance, personal usage view and
 * aggregated history.
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

/**
 * Full personal usage view (today/month, remaining allowance, current model).
 *
 * Self-invalidating on every `["usage"]` prefix change, so it refreshes after
 * each chat turn. Renders as null in the UI when it errors — see UsageIndicator.
 */
export function useUsageMe() {
  return useQuery({
    queryKey: queryKeys.usageMe,
    queryFn: () => usageApi.me(),
  });
}

/** Compact personal usage summary (tokens/requests today + this month). */
export function useUsageSummary() {
  return useQuery({
    queryKey: queryKeys.usageSummary,
    queryFn: () => usageApi.summary(),
  });
}

export function useUsageHistory(params: UsageHistoryParams = {}) {
  return useQuery({
    queryKey: queryKeys.usageHistory(params),
    queryFn: () => usageApi.history(params),
  });
}
