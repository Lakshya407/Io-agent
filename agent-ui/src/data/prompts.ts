/**
 * Mock data for Prompt Management.
 * Frontend-only demo — replace with real API responses later.
 */

export interface PromptRow {
  id: string;
  name: string;
  purpose: string;
  model: string;
  version: string;
  status: "Active" | "Draft" | "Inactive";
  updated: string;
  systemPrompt: string;
}

export const promptStats = {
  systemPrompts: 12,
  activePrompts: 8,
};

export const defaultSystemPrompt =
  "You are a helpful AI assistant. Answer clearly and use available tools when required.";

export const prompts: PromptRow[] = [
  {
    id: "p1",
    name: "Default Assistant",
    purpose: "General agent behavior",
    model: "GPT-OSS 20B",
    version: "v3",
    status: "Active",
    updated: "Today",
    systemPrompt: defaultSystemPrompt,
  },
  {
    id: "p2",
    name: "Code Assistant",
    purpose: "Code generation",
    model: "Llama 3.3 70B",
    version: "v2",
    status: "Active",
    updated: "Yesterday",
    systemPrompt:
      "You are an expert code assistant. Write clean, readable code and explain your reasoning briefly.",
  },
  {
    id: "p3",
    name: "Document Analyst",
    purpose: "Document analysis",
    model: "Qwen 2.5 72B",
    version: "v1",
    status: "Active",
    updated: "2 days ago",
    systemPrompt:
      "You are a document analyst. Summarize and extract key facts from the provided documents.",
  },
  {
    id: "p4",
    name: "Search Assistant",
    purpose: "Web and knowledge search",
    model: "GPT-OSS 20B",
    version: "v1",
    status: "Draft",
    updated: "3 days ago",
    systemPrompt:
      "You are a search assistant. Find relevant information and cite your sources.",
  },
  {
    id: "p5",
    name: "Summary Writer",
    purpose: "Conversation summarization",
    model: "Mistral Small",
    version: "v2",
    status: "Inactive",
    updated: "Last week",
    systemPrompt:
      "You are a summary writer. Produce concise summaries of long conversations.",
  },
];
