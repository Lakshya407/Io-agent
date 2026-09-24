/**
 * Prompt hooks — list, create, update and delete for the admin console.
 *
 * Prompts are a small admin-managed catalog, so the list is fetched with a
 * generous page size and stats are computed from the returned items.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { promptsApi } from "../api/prompts";
import { queryKeys } from "../lib/queryClient";
import type {
  PromptCreate,
  PromptListParams,
  PromptUpdate,
} from "../types/prompt";

const CATALOG_PAGE_SIZE = 100;

export function usePrompts(params: PromptListParams = {}) {
  const page = params.page ?? 1;
  const pageSize = params.page_size ?? CATALOG_PAGE_SIZE;
  const activeOnly = params.active_only ?? false;
  return useQuery({
    queryKey: queryKeys.prompts(page, pageSize, activeOnly),
    queryFn: () =>
      promptsApi.list({
        page,
        page_size: pageSize,
        active_only: activeOnly,
      }),
  });
}

export function useCreatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCreate) => promptsApi.create(payload),
    // Prefix invalidation also covers the `active_only` variants.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prompts"] }),
  });
}

export function useUpdatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      promptId,
      payload,
    }: {
      promptId: string;
      payload: PromptUpdate;
    }) => promptsApi.update(promptId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prompts"] }),
  });
}

export function useDeletePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (promptId: string) => promptsApi.remove(promptId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prompts"] }),
  });
}
