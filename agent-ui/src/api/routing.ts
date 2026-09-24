/**
 * Model routing API — `GET/POST /admin/routing`, `PUT /admin/routing/order`,
 * `PATCH/DELETE /admin/routing/{id}` (all admin-only).
 *
 * The list is small and unpaginated: the backend returns every rule, highest
 * priority first, so the UI can render and reorder it in one pass.
 */

import { apiFetch } from "./client";
import type {
  RoutingRule,
  RoutingRuleCreate,
  RoutingRuleUpdate,
} from "../types/routing";

export const routingApi = {
  /** `GET /api/v1/admin/routing` — every rule, highest priority first. */
  list(): Promise<RoutingRule[]> {
    return apiFetch<RoutingRule[]>("/admin/routing");
  },

  /** `POST /api/v1/admin/routing` — appends at the lowest priority (201). */
  create(payload: RoutingRuleCreate): Promise<RoutingRule> {
    return apiFetch<RoutingRule>("/admin/routing", {
      method: "POST",
      body: payload,
    });
  },

  /** `PUT /api/v1/admin/routing/order` — persist a full reordering. */
  reorder(ids: string[]): Promise<RoutingRule[]> {
    return apiFetch<RoutingRule[]>("/admin/routing/order", {
      method: "PUT",
      body: { ids },
    });
  },

  /** `PATCH /api/v1/admin/routing/{id}` — models are re-validated. */
  update(ruleId: string, payload: RoutingRuleUpdate): Promise<RoutingRule> {
    return apiFetch<RoutingRule>(`/admin/routing/${ruleId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  /** `DELETE /api/v1/admin/routing/{id}` — returns 204, renumbers the rest. */
  remove(ruleId: string): Promise<void> {
    return apiFetch<void>(`/admin/routing/${ruleId}`, { method: "DELETE" });
  },
};
