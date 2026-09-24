/**
 * Model routing types — mirror `app/schemas/routing.py`.
 */

/** `RoutingRuleOut` — one routing rule. */
export interface RoutingRule {
  id: string;
  /** 1 = evaluated first. */
  priority: number;
  request_type: string;
  primary_model: string;
  fallback_model: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** `RoutingRuleCreate` — payload for POST /api/v1/admin/routing. */
export interface RoutingRuleCreate {
  request_type: string;
  primary_model: string;
  fallback_model?: string | null;
  is_active?: boolean;
}

/** `RoutingRuleUpdate` — payload for PATCH /api/v1/admin/routing/{id}. */
export interface RoutingRuleUpdate {
  request_type?: string;
  primary_model?: string;
  fallback_model?: string | null;
  is_active?: boolean;
  priority?: number;
}

/** `RoutingRuleOrder` — payload for PUT /api/v1/admin/routing/order. */
export interface RoutingRuleOrder {
  /** Every rule id exactly once, highest priority first. */
  ids: string[];
}
