/**
 * Prompt management types — mirror `app/schemas/prompt.py`.
 */

import type { PageParams } from "./common";

export type PromptStatus = "active" | "draft" | "inactive";

/** `PromptOut` — one prompt as returned by the admin prompts API. */
export interface Prompt {
  id: string;
  name: string;
  purpose: string;
  model: string | null;
  version: number;
  status: PromptStatus;
  content: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

/** `PromptCreate` — payload for POST /api/v1/prompts. */
export interface PromptCreate {
  name: string;
  purpose?: string;
  model?: string | null;
  version?: number;
  status?: PromptStatus;
  content: string;
  is_default?: boolean;
}

/** `PromptUpdate` — payload for PATCH /api/v1/prompts/{id}; all optional. */
export interface PromptUpdate {
  name?: string;
  purpose?: string;
  model?: string | null;
  version?: number;
  status?: PromptStatus;
  content?: string;
  is_default?: boolean;
}

/** Query params for GET /api/v1/prompts. */
export interface PromptListParams extends PageParams {
  /** Only prompts whose `status` is `active`. */
  active_only?: boolean;
}
