/**
 * Model hooks — list, create, update, status toggle and delete.
 *
 * Model configs are a small admin-managed catalog, so the list is fetched
 * with a generous page size and stats are computed from the returned items.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { modelsApi } from "../api/models";
import { queryKeys } from "../lib/queryClient";
import type { ModelCreate, ModelUpdate } from "../types/model";

const CATALOG_PAGE_SIZE = 100;

export function useModels({ activeOnly = false }: { activeOnly?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.models(1, CATALOG_PAGE_SIZE, activeOnly),
    queryFn: () =>
      modelsApi.list({
        page: 1,
        page_size: CATALOG_PAGE_SIZE,
        active_only: activeOnly,
        // Admin management view needs availability; the chat dropdown does
        // not (avoids an Ollama call on every chat render).
        include_availability: !activeOnly,
      }),
  });
}

export function useCreateModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ModelCreate) => modelsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useUpdateModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      modelId,
      payload,
    }: {
      modelId: string;
      payload: ModelUpdate;
    }) => modelsApi.update(modelId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useToggleModelStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      modelId,
      isActive,
    }: {
      modelId: string;
      isActive: boolean;
    }) => modelsApi.setStatus(modelId, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useDeleteModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modelId: string) => modelsApi.remove(modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useSetDefaultModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modelId: string) => modelsApi.setDefault(modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}
