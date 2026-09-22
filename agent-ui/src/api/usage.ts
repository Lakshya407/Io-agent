/**
 * Usage API — `GET /usage`, `GET /usage/history`.
 */

import { apiFetch } from "./client";
import type { PaginatedResponse } from "../types/common";
import type { Usage, UsageHistoryItem, UsageHistoryParams } from "../types/usage";

export const usageApi = {
  /** `GET /api/v1/usage` — the current user's allowance. */
  current(): Promise<Usage> {
    return apiFetch<Usage>("/usage");
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
