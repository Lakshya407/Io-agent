import { Download, ScrollText } from "lucide-react";
import { useMemo, useState } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import FilterBar from "../../components/admin/FilterBar";
import PageHeader from "../../components/admin/PageHeader";
import Pagination from "../../components/admin/Pagination";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useAuditLogs } from "../../hooks/useAuditLogs";
import { useUsers } from "../../hooks/useUsers";
import { toAuditLogRow, type AuditLogRow } from "../../utils/adapters";
import type { AuditAction } from "../../types/admin";

const PAGE_SIZE = 20;

const ACTION_OPTIONS: AuditAction[] = [
  "USER_LOGIN",
  "USER_LOGOUT",
  "USER_CREATED",
  "USER_UPDATED",
  "USER_DELETED",
  "MODEL_CREATED",
  "MODEL_UPDATED",
  "MODEL_DISABLED",
  "TOOL_CREATED",
  "TOOL_UPDATED",
  "TOOL_DISABLED",
  "USAGE_LIMIT_UPDATED",
  "API_KEY_CREATED",
  "API_KEY_REVOKED",
];

const ACTION_LABELS: Record<string, string> = {
  USER_LOGIN: "Signed in",
  USER_LOGOUT: "Signed out",
  USER_CREATED: "Created user",
  USER_UPDATED: "Updated user",
  USER_DELETED: "Deleted user",
  MODEL_CREATED: "Created model",
  MODEL_UPDATED: "Updated model",
  MODEL_DISABLED: "Updated model status",
  TOOL_CREATED: "Created tool",
  TOOL_UPDATED: "Updated tool",
  TOOL_DISABLED: "Updated tool status",
  USAGE_LIMIT_UPDATED: "Updated allowance",
  API_KEY_CREATED: "Created API key",
  API_KEY_REVOKED: "Revoked API key",
};

export default function AdminAuditLogs() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [user, setUser] = useState("");

  const { data: usersData } = useUsers({ page: 1, page_size: 100 });
  const userNameById = useMemo(() => {
    const map: Record<string, string> = {};
    usersData?.items.forEach((u) => {
      map[u.id] = u.name || u.email;
    });
    return map;
  }, [usersData]);

  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useAuditLogs({
    page,
    page_size: PAGE_SIZE,
    action: (action || undefined) as AuditAction | undefined,
    user_id: user || undefined,
  });

  const rows = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (data?.items ?? [])
      .map((log) => toAuditLogRow(log, userNameById))
      .filter((row) => {
        if (!query) return true;
        return (
          row.user.toLowerCase().includes(query) ||
          row.action.toLowerCase().includes(query) ||
          row.resource.toLowerCase().includes(query)
        );
      });
  }, [data, userNameById, search]);

  const columns: Column<AuditLogRow>[] = [
    { key: "timestamp", header: "Timestamp", render: (row) => row.timestamp },
    { key: "user", header: "User", render: (row) => row.user },
    { key: "action", header: "Action", render: (row) => row.action },
    { key: "resource", header: "Resource", render: (row) => row.resource },
    { key: "ip", header: "IP Address", render: (row) => row.ip },
  ];

  const exportCsv = () => {
    const header = ["Timestamp", "User", "Action", "Resource", "IP"];
    const lines = rows.map((row) =>
      [row.timestamp, row.user, row.action, row.resource, row.ip].join(","),
    );
    const csv = [header.join(","), ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "audit-logs.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="admin-content">
      <PageHeader
        title="Audit Logs"
        subtitle="Administrator and system activity history."
        actions={
          <button
            type="button"
            className="btn btn-secondary"
            onClick={exportCsv}
            disabled={rows.length === 0}
          >
            <Download size={15} />
            Export
          </button>
        }
      />

      <section className="admin-card">
        <div className="card-head">
          <h2>Audit Trail</h2>
          <div className="card-head-note">
            <ScrollText size={14} />
            <span className="card-badge">
              {data ? `${data.total} entries` : "Loading…"}
            </span>
          </div>
        </div>
        <FilterBar
          searchValue={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search logs…"
          filters={[
            {
              label: "Action",
              value: action,
              options: ACTION_OPTIONS.map((a) => ({
                value: a,
                label: ACTION_LABELS[a] ?? a,
              })),
              onChange: (value) => {
                setAction(value);
                setPage(1);
              },
            },
            {
              label: "User",
              value: user,
              options: (usersData?.items ?? []).map((u) => ({
                value: u.id,
                label: u.name || u.email,
              })),
              onChange: (value) => {
                setUser(value);
                setPage(1);
              },
            },
          ]}
        />
        {isLoading ? (
          <LoadingState label="Loading audit logs…" />
        ) : error ? (
          <ErrorState
            error={error}
            context="Unable to load audit logs."
            onRetry={() => refetch()}
          />
        ) : (
          <>
            <DataTable
              columns={columns}
              rows={rows}
              rowKey={(row) => row.id}
              emptyMessage="No audit entries match the selected filters."
            />
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={data?.total ?? 0}
              onPageChange={setPage}
              loading={isFetching}
            />
          </>
        )}
      </section>
    </div>
  );
}
