/**
 * Rate limit hooks — rule CRUD plus today's Redis-backed counters.
 *
 * `["rate-limits"]` is a prefix of `["rate-limits", "stats"]`, so a single
 * invalidation refreshes both the rule list and the stats cards.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { rateLimitsApi } from "../api/rateLimits";
import { queryKeys } from "../lib/queryClient";
import type { RateLimitRuleCreate, RateLimitRuleUpdate } from "../types/rateLimit";

export function useRateLimitRules() {
  return useQuery({
    queryKey: queryKeys.rateLimits,
    queryFn: () => rateLimitsApi.list(),
  });
}

/** Today's counters — refreshes whenever the rules are mutated. */
export function useRateLimitStats() {
  return useQuery({
    queryKey: queryKeys.rateLimitStats,
    queryFn: () => rateLimitsApi.stats(),
  });
}

export function useCreateRateLimitRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RateLimitRuleCreate) => rateLimitsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.rateLimits });
    },
  });
}

export function useUpdateRateLimitRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      ruleId,
      payload,
    }: {
      ruleId: string;
      payload: RateLimitRuleUpdate;
    }) => rateLimitsApi.update(ruleId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.rateLimits });
    },
  });
}

export function useDeleteRateLimitRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => rateLimitsApi.remove(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.rateLimits });
    },
  });
}
