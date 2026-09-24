/**
 * Routing hooks — list, CRUD and full reordering for the admin console.
 *
 * The rule list is unpaginated, so every mutation invalidates the single
 * `["routing"]` key.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { routingApi } from "../api/routing";
import { queryKeys } from "../lib/queryClient";
import type {
  RoutingRuleCreate,
  RoutingRuleUpdate,
} from "../types/routing";

export function useRoutingRules() {
  return useQuery({
    queryKey: queryKeys.routing,
    queryFn: () => routingApi.list(),
  });
}

export function useCreateRoutingRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RoutingRuleCreate) => routingApi.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.routing }),
  });
}

export function useUpdateRoutingRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      ruleId,
      payload,
    }: {
      ruleId: string;
      payload: RoutingRuleUpdate;
    }) => routingApi.update(ruleId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.routing }),
  });
}

/** Swap two adjacent rules by sending the whole ordered id list. */
export function useReorderRoutingRules() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => routingApi.reorder(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.routing }),
  });
}

export function useDeleteRoutingRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => routingApi.remove(ruleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.routing }),
  });
}
