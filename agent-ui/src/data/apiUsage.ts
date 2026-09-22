/**
 * Mock data for API Usage monitoring.
 * Frontend-only demo — replace with real API responses later.
 */

export interface ApiUsageRow {
  api: string;
  requests: string;
  tokens: string;
  successRate: string;
  avgResponseTime: string;
  status: "Active" | "Inactive";
}

export const apiUsageStats = {
  totalRequests: "8,420",
  successfulRequests: "8,210",
  failedRequests: "210",
  avgResponseTime: "1.4s",
};

export const apiUsage: ApiUsageRow[] = [
  {
    api: "Chat API",
    requests: "4,820",
    tokens: "4.2M",
    successRate: "99.2%",
    avgResponseTime: "1.2s",
    status: "Active",
  },
  {
    api: "Search API",
    requests: "2,140",
    tokens: "1.8M",
    successRate: "98.8%",
    avgResponseTime: "1.6s",
    status: "Active",
  },
  {
    api: "Document API",
    requests: "820",
    tokens: "900K",
    successRate: "97.9%",
    avgResponseTime: "2.1s",
    status: "Active",
  },
  {
    api: "Agent API",
    requests: "640",
    tokens: "900K",
    successRate: "99.4%",
    avgResponseTime: "1.1s",
    status: "Active",
  },
];
