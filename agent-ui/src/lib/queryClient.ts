/**
 * TanStack Query client — caching, request deduplication, loading/error
 * states and cache invalidation for every server-state query.
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Server data is the source of truth; stay fresh but avoid hammering.
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => {
        // The API client already retries idempotent GETs once for transient
        // failures; do not stack additional React Query retries.
        if (error instanceof Error && "status" in error) {
          const status = (error as { status: number }).status;
          if (status === 401 || status === 403 || status === 404) return false;
        }
        return failureCount < 1;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      // Mutations are never retried automatically (no idempotency guarantees).
      retry: false,
    },
  },
});

/** Centralised query-key factory so invalidation stays consistent. */
export const queryKeys = {
  auth: ["auth", "me"] as const,
  dashboard: ["admin", "dashboard"] as const,
  users: (page: number, pageSize: number) =>
    ["users", { page, pageSize }] as const,
  user: (userId: string) => ["users", userId] as const,
  models: (page: number, pageSize: number, activeOnly: boolean) =>
    ["models", { page, pageSize, activeOnly }] as const,
  tools: (page: number, pageSize: number, activeOnly: boolean) =>
    ["tools", { page, pageSize, activeOnly }] as const,
  usage: ["usage", "current"] as const,
  usageMe: ["usage", "me"] as const,
  usageSummary: ["usage", "summary"] as const,
  usageHistory: (params: object) => ["usage", "history", params] as const,
  adminUsage: (page: number, pageSize: number) =>
    ["admin", "usage", { page, pageSize }] as const,
  adminUsageSummary: (params: object) =>
    ["admin", "usage", "summary", params] as const,
  adminUsageUsers: (params: object) =>
    ["admin", "usage", "users", params] as const,
  adminUsageModels: (params: object) =>
    ["admin", "usage", "models", params] as const,
  adminUsageTimeline: (params: object) =>
    ["admin", "usage", "timeline", params] as const,
  auditLogs: (params: object) => ["admin", "audit-logs", params] as const,
  prompts: (page: number, pageSize: number, activeOnly: boolean) =>
    ["prompts", { page, pageSize, activeOnly }] as const,
  routing: ["routing"] as const,
  rateLimits: ["rate-limits"] as const,
  rateLimitStats: ["rate-limits", "stats"] as const,
  conversations: (page: number, pageSize: number) =>
    ["conversations", { page, pageSize }] as const,
  conversationMessages: (conversationId: string) =>
    ["conversations", conversationId, "messages"] as const,
};
