/**
 * Usage API — `GET /usage`, `/usage/me`, `/usage/summary`, `/usage/history`.
 */

import { apiFetch } from "./client";
import type { PaginatedResponse } from "../types/common";
import type {
  Usage,
  UsageHistoryItem,
  UsageHistoryParams,
  UsageMe,
  UsageSummary,
} from "../types/usage";

export const usageApi = {
  /** `GET /api/v1/usage` — the current user's allowance. */
  current(): Promise<Usage> {
    return apiFetch<Usage>("/usage");
  },

  /** `GET /api/v1/usage/me` — today/month usage + remaining + current model. */
  me(): Promise<UsageMe> {
    return apiFetch<UsageMe>("/usage/me");
  },

  /** `GET /api/v1/usage/summary` — compact personal usage summary. */
  summary(): Promise<UsageSummary> {
    return apiFetch<UsageSummary>("/usage/summary");
  },

  /** `GET /api/v1/usage/history` — aggregated daily usage for the user. */
  history(params: UsageHistoryParams = {}): Promise<
    PaginatedResponse<UsageHistoryItem>
  > {
    return apiFetch<PaginatedResponse<UsageHistoryItem>>("/usage/history", {
      params,
    });
  },
};
