/**
 * Audit logs API — `GET /admin/audit-logs`.
 */

import { apiFetch } from "./client";
import type { PaginatedResponse } from "../types/common";
import type { AuditLog, AuditLogParams } from "../types/admin";

export const auditLogsApi = {
  /** `GET /api/v1/admin/audit-logs` — newest first. */
  list(params: AuditLogParams = {}): Promise<PaginatedResponse<AuditLog>> {
    return apiFetch<PaginatedResponse<AuditLog>>("/admin/audit-logs", {
      params,
    });
  },
};
