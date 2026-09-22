/**
 * Models API — public list/detail + admin CRUD.
 */

import { apiFetch } from "./client";
import type { PaginatedResponse, PageParams } from "../types/common";
import type {
  Model,
  ModelCreate,
  ModelStatusUpdate,
  ModelUpdate,
} from "../types/model";

export interface ModelListParams extends PageParams {
  /** Set to false to include disabled models (default true). */
  active_only?: boolean;
}

export const modelsApi = {
  /** `GET /api/v1/models` — list models. */
  list(params: ModelListParams = {}): Promise<PaginatedResponse<Model>> {
    return apiFetch<PaginatedResponse<Model>>("/models", { params });
  },

  /** `GET /api/v1/models/{id}`. */
  get(modelId: string): Promise<Model> {
    return apiFetch<Model>(`/models/${modelId}`);
  },

  /** `POST /api/v1/admin/models` — returns 201. */
  create(payload: ModelCreate): Promise<Model> {
    return apiFetch<Model>("/admin/models", { method: "POST", body: payload });
  },

  /** `PUT /api/v1/admin/models/{id}`. */
  update(modelId: string, payload: ModelUpdate): Promise<Model> {
    return apiFetch<Model>(`/admin/models/${modelId}`, {
      method: "PUT",
      body: payload,
    });
  },

  /** `PATCH /api/v1/admin/models/{id}/status`. */
  setStatus(modelId: string, payload: ModelStatusUpdate): Promise<Model> {
    return apiFetch<Model>(`/admin/models/${modelId}/status`, {
      method: "PATCH",
      body: payload,
    });
  },

  /** `DELETE /api/v1/admin/models/{id}` — returns 204. */
  remove(modelId: string): Promise<void> {
    return apiFetch<void>(`/admin/models/${modelId}`, { method: "DELETE" });
  },
};
