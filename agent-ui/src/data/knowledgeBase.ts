/**
 * Mock data for the Knowledge Base page.
 * Frontend-only demo — no documents are actually processed.
 */

export interface KnowledgeBaseRow {
  id: string;
  name: string;
  description: string;
  documents: number;
  indexed: number;
  size: string;
  status: "Ready" | "Processing" | "Failed";
  updated: string;
  embeddingModel: string;
}

export const kbStats = {
  total: 14,
  documents: "1,284",
  indexed: "1,240",
  storageUsed: "8.4 GB",
};

export const knowledgeBases: KnowledgeBaseRow[] = [
  {
    id: "kb1",
    name: "Company Documentation",
    description: "Policies, HR and internal process documents.",
    documents: 420,
    indexed: 418,
    size: "2.1 GB",
    status: "Ready",
    updated: "Today",
    embeddingModel: "text-embedding-3-small",
  },
  {
    id: "kb2",
    name: "Product Documentation",
    description: "Product specs, user guides and release notes.",
    documents: 320,
    indexed: 315,
    size: "1.8 GB",
    status: "Ready",
    updated: "Yesterday",
    embeddingModel: "text-embedding-3-small",
  },
  {
    id: "kb3",
    name: "Technical Docs",
    description: "Architecture, API references and runbooks.",
    documents: 544,
    indexed: 507,
    size: "4.5 GB",
    status: "Processing",
    updated: "Today",
    embeddingModel: "text-embedding-3-large",
  },
  {
    id: "kb4",
    name: "Onboarding Guides",
    description: "New hire and team onboarding material.",
    documents: 128,
    indexed: 120,
    size: "1.2 GB",
    status: "Ready",
    updated: "2 days ago",
    embeddingModel: "text-embedding-3-small",
  },
];

export const embeddingModelOptions: string[] = [
  "text-embedding-3-small",
  "text-embedding-3-large",
];
