/**
 * Response adapters.
 *
 * The backend is the source of truth; these functions only translate its
 * response shapes into the field names the existing UI components expect,
 * so components and their styling stay untouched.
 */

import type { AdminUsageRow, AuditLog } from "../types/admin";
import type { User } from "../types/auth";
import type { Conversation } from "../types/chat";
import type { Model } from "../types/model";
import type { Tool } from "../types/tool";
import { formatRelativeTime } from "./format";

/** Row shape consumed by the existing users `DataTable`. */
export interface UserRow {
  id: string;
  name: string;
  email: string;
  status: "Active" | "Inactive";
  role: "Admin" | "User";
  created: string;
}

export function toUserRow(user: User): UserRow {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    status: user.is_active ? "Active" : "Inactive",
    role: user.role === "admin" ? "Admin" : "User",
    created: formatRelativeTime(user.created_at),
  };
}

/** Row shape consumed by the existing models `DataTable`. */
export interface ModelRow {
  id: string;
  name: string;
  provider: string;
  type: string;
  status: "Active" | "Inactive";
  isDefault: boolean;
  created: string;
  maxTokens: number;
  temperature: number;
  modelIdentifier: string;
}

export function toModelRow(model: Model): ModelRow {
  return {
    id: model.id,
    name: model.name,
    provider: model.provider,
    type: model.model_type,
    status: model.is_active ? "Active" : "Inactive",
    isDefault: model.is_default,
    created: formatRelativeTime(model.created_at),
    maxTokens: model.max_tokens,
    temperature: model.temperature,
    modelIdentifier: model.model_identifier,
  };
}

/** Row shape consumed by the existing tools `DataTable`. */
export interface ToolRow {
  id: string;
  name: string;
  description: string;
  category: string;
  status: "Active" | "Inactive";
  updated: string;
}

export function toToolRow(tool: Tool): ToolRow {
  return {
    id: tool.id,
    name: tool.name,
    description: tool.description,
    category: tool.type,
    status: tool.is_active ? "Active" : "Inactive",
    updated: formatRelativeTime(tool.updated_at),
  };
}

/** Row shape consumed by the admin usage `DataTable`. */
export interface AdminUsageTableRow {
  id: string;
  name: string;
  email: string;
  role: "Admin" | "User";
  tokensUsed: number;
  requestsUsed: number;
  tokensRemaining: number;
  requestsRemaining: number;
  monthlyTokenLimit: number;
  monthlyRequestLimit: number;
  resetAt: string;
}

export function toAdminUsageTableRow(row: AdminUsageRow): AdminUsageTableRow {
  return {
    id: row.user_id,
    name: row.name,
    email: row.email,
    role: row.role === "admin" ? "Admin" : "User",
    tokensUsed: row.tokens_used,
    requestsUsed: row.requests_used,
    tokensRemaining: row.tokens_remaining,
    requestsRemaining: row.requests_remaining,
    monthlyTokenLimit: row.monthly_token_limit,
    monthlyRequestLimit: row.monthly_request_limit,
    resetAt: row.reset_at,
  };
}

/** Row shape consumed by the audit-log `DataTable`. */
export interface AuditLogRow {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  ip: string;
  status: "Success" | "System";
}

/** Human-friendly label for a machine audit action. */
const ACTION_LABELS: Record<string, string> = {
  USER_LOGIN: "Signed in",
  USER_LOGOUT: "Signed out",
  USER_CREATED: "Created user",
  USER_UPDATED: "Updated user",
  USER_DELETED: "Deleted user",
  MODEL_CREATED: "Created model",
  MODEL_UPDATED: "Updated model",
  MODEL_DISABLED: "Toggled model",
  TOOL_CREATED: "Created tool",
  TOOL_UPDATED: "Updated tool",
  TOOL_DISABLED: "Toggled tool",
  USAGE_LIMIT_UPDATED: "Updated allowance",
  API_KEY_CREATED: "Created API key",
  API_KEY_REVOKED: "Revoked API key",
};

export function toAuditLogRow(
  log: AuditLog,
  userNameById: Record<string, string>,
): AuditLogRow {
  const actor = log.user_id
    ? (userNameById[log.user_id] ?? "user")
    : "system";
  return {
    id: log.id,
    timestamp: formatRelativeTime(log.created_at),
    user: actor,
    action: ACTION_LABELS[log.action] ?? log.action,
    resource: [log.resource_type, log.resource_id].filter(Boolean).join(" · "),
    ip: log.ip_address ?? "—",
    status: log.action.endsWith("_FAILED") ? "System" : "Success",
  };
}

/** Conversation sidebar entry. */
export interface ConversationRow {
  id: string;
  title: string;
  group: string;
}

export function toConversationRow(conversation: Conversation): ConversationRow {
  const date = new Date(conversation.updated_at);
  const group = Number.isNaN(date.getTime())
    ? "Earlier"
    : date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
  return {
    id: conversation.id,
    title: conversation.title,
    group,
  };
}
