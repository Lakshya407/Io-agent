/**
 * Tools API — public list/detail + admin CRUD.
 */

import { apiFetch } from "./client";
import type { PaginatedResponse, PageParams } from "../types/common";
import type { Tool, ToolCreate, ToolStatusUpdate, ToolUpdate } from "../types/tool";

export interface ToolListParams extends PageParams {
  /** Set to false to include disabled tools (default true). */
  active_only?: boolean;
}

export const toolsApi = {
  /** `GET /api/v1/tools` — list tools. */
  list(params: ToolListParams = {}): Promise<PaginatedResponse<Tool>> {
    return apiFetch<PaginatedResponse<Tool>>("/tools", { params });
  },

  /** `GET /api/v1/tools/{id}`. */
  get(toolId: string): Promise<Tool> {
    return apiFetch<Tool>(`/tools/${toolId}`);
  },

  /** `POST /api/v1/admin/tools` — returns 201. */
  create(payload: ToolCreate): Promise<Tool> {
    return apiFetch<Tool>("/admin/tools", { method: "POST", body: payload });
  },

  /** `PUT /api/v1/admin/tools/{id}`. */
  update(toolId: string, payload: ToolUpdate): Promise<Tool> {
    return apiFetch<Tool>(`/admin/tools/${toolId}`, {
      method: "PUT",
      body: payload,
    });
  },

  /** `PATCH /api/v1/admin/tools/{id}/status`. */
  setStatus(toolId: string, payload: ToolStatusUpdate): Promise<Tool> {
    return apiFetch<Tool>(`/admin/tools/${toolId}/status`, {
      method: "PATCH",
      body: payload,
    });
  },

  /** `DELETE /api/v1/admin/tools/{id}` — returns 204. */
  remove(toolId: string): Promise<void> {
    return apiFetch<void>(`/admin/tools/${toolId}`, { method: "DELETE" });
  },
};
