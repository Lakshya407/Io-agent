/**
 * Tool hooks — list, create, update, status toggle and delete.
 *
 * Tool configs are a small admin-managed catalog, so the list is fetched
 * with a generous page size and stats are computed from the returned items.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toolsApi } from "../api/tools";
import { queryKeys } from "../lib/queryClient";
import type { ToolCreate, ToolUpdate } from "../types/tool";

const CATALOG_PAGE_SIZE = 100;

export function useTools({ activeOnly = false }: { activeOnly?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.tools(1, CATALOG_PAGE_SIZE, activeOnly),
    queryFn: () =>
      toolsApi.list({
        page: 1,
        page_size: CATALOG_PAGE_SIZE,
        active_only: activeOnly,
      }),
  });
}

export function useCreateTool() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ToolCreate) => toolsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useUpdateTool() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      toolId,
      payload,
    }: {
      toolId: string;
      payload: ToolUpdate;
    }) => toolsApi.update(toolId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useToggleToolStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      toolId,
      isActive,
    }: {
      toolId: string;
      isActive: boolean;
    }) => toolsApi.setStatus(toolId, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useDeleteTool() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (toolId: string) => toolsApi.remove(toolId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tools"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}
