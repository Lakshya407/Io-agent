/**
 * Prompts API — `GET/POST /prompts`, `GET/PATCH/DELETE /prompts/{id}`
 * (all admin-only).
 */

import { apiFetch } from "./client";
import type { PaginatedResponse } from "../types/common";
import type {
  Prompt,
  PromptCreate,
  PromptListParams,
  PromptUpdate,
} from "../types/prompt";

export const promptsApi = {
  /** `GET /api/v1/prompts` — one page of prompts, newest first. */
  list(params: PromptListParams = {}): Promise<PaginatedResponse<Prompt>> {
    return apiFetch<PaginatedResponse<Prompt>>("/prompts", { params });
  },

  /** `POST /api/v1/prompts` — names are unique (201). */
  create(payload: PromptCreate): Promise<Prompt> {
    return apiFetch<Prompt>("/prompts", { method: "POST", body: payload });
  },

  /** `GET /api/v1/prompts/{id}`. */
  get(promptId: string): Promise<Prompt> {
    return apiFetch<Prompt>(`/prompts/${promptId}`);
  },

  /** `PATCH /api/v1/prompts/{id}` — partially update a prompt. */
  update(promptId: string, payload: PromptUpdate): Promise<Prompt> {
    return apiFetch<Prompt>(`/prompts/${promptId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  /** `DELETE /api/v1/prompts/{id}` — returns 204. */
  remove(promptId: string): Promise<void> {
    return apiFetch<void>(`/prompts/${promptId}`, { method: "DELETE" });
  },
};
