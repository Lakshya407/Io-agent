/**
 * Audit log hooks — paginated, filterable admin audit trail.
 */

import { useQuery } from "@tanstack/react-query";
import { auditLogsApi } from "../api/auditLogs";
import { queryKeys } from "../lib/queryClient";
import type { AuditLogParams } from "../types/admin";

const DEFAULT_PAGE_SIZE = 20;

export function useAuditLogs(params: AuditLogParams = {}) {
  return useQuery({
    queryKey: queryKeys.auditLogs({
      action: params.action ?? "",
      resource_type: params.resource_type ?? "",
      user_id: params.user_id ?? "",
      page: params.page ?? 1,
      page_size: params.page_size ?? DEFAULT_PAGE_SIZE,
    }),
    queryFn: () =>
      auditLogsApi.list({
        ...params,
        page: params.page ?? 1,
        page_size: params.page_size ?? DEFAULT_PAGE_SIZE,
      }),
  });
}
