/**
 * Mock data for Models + Model Routing.
 * Frontend-only demo — replace with real API responses later.
 */

export interface ModelRow {
  id: string;
  name: string;
  provider: string;
  type: string;
  status: "Active" | "Inactive";
  requests: number;
  tokens: string;
  created: string;
  contextLength: string;
}

export interface RoutingRule {
  id: string;
  priority: number;
  requestType: string;
  primaryModel: string;
  fallbackModel: string;
  status: "Active" | "Inactive";
}

export const modelStats = {
  total: 12,
  active: 8,
  inactive: 4,
  createdThisMonth: 3,
};

export const models: ModelRow[] = [
  {
    id: "m1",
    name: "GPT-OSS 20B",
    provider: "Open Source",
    type: "Chat",
    status: "Active",
    requests: 820,
    tokens: "2.4M",
    created: "01 Sep 2026",
    contextLength: "128K",
  },
  {
    id: "m2",
    name: "Qwen 2.5 72B",
    provider: "Open Source",
    type: "Chat",
    status: "Active",
    requests: 640,
    tokens: "1.8M",
    created: "03 Sep 2026",
    contextLength: "128K",
  },
  {
    id: "m3",
    name: "Llama 3.3 70B",
    provider: "Open Source",
    type: "Chat",
    status: "Active",
    requests: 510,
    tokens: "1.5M",
    created: "05 Sep 2026",
    contextLength: "128K",
  },
  {
    id: "m4",
    name: "Mistral Small",
    provider: "Open Source",
    type: "Chat",
    status: "Inactive",
    requests: 460,
    tokens: "1.1M",
    created: "08 Sep 2026",
    contextLength: "32K",
  },
  {
    id: "m5",
    name: "CodeLlama 34B",
    provider: "Open Source",
    type: "Code",
    status: "Inactive",
    requests: 180,
    tokens: "640K",
    created: "12 Sep 2026",
    contextLength: "16K",
  },
];

export const routingRules: RoutingRule[] = [
  {
    id: "r1",
    priority: 1,
    requestType: "General Chat",
    primaryModel: "GPT-OSS 20B",
    fallbackModel: "Mistral Small",
    status: "Active",
  },
  {
    id: "r2",
    priority: 2,
    requestType: "Code",
    primaryModel: "Llama 3.3 70B",
    fallbackModel: "GPT-OSS 20B",
    status: "Active",
  },
  {
    id: "r3",
    priority: 3,
    requestType: "Document Analysis",
    primaryModel: "Qwen 2.5 72B",
    fallbackModel: "Llama 3.3 70B",
    status: "Active",
  },
  {
    id: "r4",
    priority: 4,
    requestType: "Complex Reasoning",
    primaryModel: "Qwen 2.5 72B",
    fallbackModel: "GPT-OSS 20B",
    status: "Active",
  },
];

export const modelOptions: string[] = [
  "GPT-OSS 20B",
  "Qwen 2.5 72B",
  "Llama 3.3 70B",
  "Mistral Small",
];

export const requestTypeOptions: string[] = [
  "General Chat",
  "Complex Reasoning",
  "Code Generation",
  "Document Analysis",
];
