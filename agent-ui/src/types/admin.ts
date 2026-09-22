/**
 * Admin types — mirror `app/schemas/admin.py` and `app/models/audit_log.py`.
 */

import type { UserRole } from "./auth";

/** `DashboardStats` — returned by GET /api/v1/admin/dashboard. */
export interface DashboardStats {
  total_users: number;
  active_users: number;
  total_requests: number;
  total_tokens: number;
  active_models: number;
  active_tools: number;
}

/** `AdminUsageRow` — allowance joined with user identity (admin views). */
export interface AdminUsageRow {
  user_id: string;
  email: string;
  name: string;
  role: UserRole;
  monthly_token_limit: number;
  monthly_request_limit: number;
  tokens_used: number;
  requests_used: number;
  tokens_remaining: number;
  requests_remaining: number;
  reset_at: string;
}

/** `AuditAction` — actions recorded by the audit service. */
export type AuditAction =
  | "USER_LOGIN"
  | "USER_LOGOUT"
  | "USER_CREATED"
  | "USER_UPDATED"
  | "USER_DELETED"
  | "MODEL_CREATED"
  | "MODEL_UPDATED"
  | "MODEL_DISABLED"
  | "TOOL_CREATED"
  | "TOOL_UPDATED"
  | "TOOL_DISABLED"
  | "USAGE_LIMIT_UPDATED"
  | "API_KEY_CREATED"
  | "API_KEY_REVOKED";

/** `AuditLogOut` — an immutable audit event. */
export interface AuditLog {
  id: string;
  user_id?: string | null;
  action: AuditAction;
  resource_type: string;
  resource_id?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

/** Query params for GET /api/v1/admin/audit-logs. */
export interface AuditLogParams {
  action?: AuditAction;
  resource_type?: string;
  user_id?: string;
  page?: number;
  page_size?: number;
}
