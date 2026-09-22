/**
 * Mock data for Agent Activity.
 * Frontend-only demo — replace with real API responses later.
 */

export interface AgentActivityRow {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  tool: string;
  model: string;
  status: "Completed" | "In Progress" | "Failed";
}

export const agentActivity: AgentActivityRow[] = [
  {
    id: "ac1",
    timestamp: "09:47",
    user: "User01",
    action: "Document Search",
    tool: "Document Search Tool",
    model: "Qwen 2.5 72B",
    status: "Completed",
  },
  {
    id: "ac2",
    timestamp: "09:43",
    user: "User02",
    action: "Code Generation",
    tool: "Code Execution",
    model: "Llama 3.3 70B",
    status: "Completed",
  },
  {
    id: "ac3",
    timestamp: "09:41",
    user: "User03",
    action: "General Chat",
    tool: "None",
    model: "GPT-OSS 20B",
    status: "Completed",
  },
  {
    id: "ac4",
    timestamp: "09:32",
    user: "User04",
    action: "Data Analysis",
    tool: "Data Analysis",
    model: "GPT-OSS 20B",
    status: "In Progress",
  },
  {
    id: "ac5",
    timestamp: "09:15",
    user: "User02",
    action: "Web Search",
    tool: "Web Search",
    model: "Mistral Small",
    status: "Failed",
  },
];
