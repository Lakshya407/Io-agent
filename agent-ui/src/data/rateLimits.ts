/**
 * Mock data for Rate Limiting.
 * Frontend-only demo — no requests are actually blocked.
 */

export interface RateLimitRule {
  id: string;
  scope: string;
  limit: number;
  window: string;
  action: string;
  status: "Active" | "Inactive";
}

export const rateLimitStats = {
  requestsToday: "8,420",
  requestsBlocked: "120",
  violations: "42",
};

export const rateLimitRules: RateLimitRule[] = [
  {
    id: "rl1",
    scope: "All Users",
    limit: 100,
    window: "1 hour",
    action: "Block request",
    status: "Active",
  },
  {
    id: "rl2",
    scope: "API",
    limit: 1000,
    window: "1 hour",
    action: "Block request",
    status: "Active",
  },
  {
    id: "rl3",
    scope: "Model",
    limit: 500,
    window: "1 hour",
    action: "Queue request",
    status: "Active",
  },
  {
    id: "rl4",
    scope: "Premium User",
    limit: 500,
    window: "1 hour",
    action: "Notify admin",
    status: "Active",
  },
];

export const rateLimitWindowOptions: string[] = [
  "1 minute",
  "1 hour",
  "1 day",
  "1 month",
];

export const rateLimitActionOptions: string[] = [
  "Block request",
  "Queue request",
  "Notify admin",
];
