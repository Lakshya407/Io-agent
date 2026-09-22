import { Pencil } from "lucide-react";
import { useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import Pagination from "../../components/admin/Pagination";
import ProgressBar from "../../components/admin/ProgressBar";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import {
  useAdminDashboard,
  useAdminUsage,
  useUpdateAllowance,
} from "../../hooks/useAdmin";
import { useUsage, useUsageHistory } from "../../hooks/useUsage";
import {
  formatNumber,
  formatRelativeTime,
  formatTokens,
  usagePercent,
} from "../../utils/format";
import { toAdminUsageTableRow, type AdminUsageTableRow } from "../../utils/adapters";
import { APIError } from "../../types/common";
import type { AllowanceUpdate } from "../../types/usage";

const PAGE_SIZE = 20;

export default function AdminUsage() {
  const { data: usage, isLoading: usageLoading } = useUsage();
  const {
    data: history,
    isLoading: historyLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useUsageHistory({ page_size: 10 });
  const [adminPage, setAdminPage] = useState(1);
  const {
    data: adminUsage,
    isLoading: adminLoading,
    error: adminError,
    refetch: refetchAdminUsage,
    isFetching: adminFetching,
  } = useAdminUsage({ page: adminPage, page_size: PAGE_SIZE });
  const { data: dashboard } = useAdminDashboard();
  const allowanceMutation = useUpdateAllowance();
  const { toast } = useToast();
  const [editing, setEditing] = useState<AdminUsageTableRow | null>(null);
  const [formError, setFormError] = useState("");

  const allowance = usage
    ? {
        percent: usagePercent(usage.tokens_used, usage.monthly_token_limit),
      }
    : null;

  const submitAllowance = async (event: FormEvent) => {
    event.preventDefault();
    if (!editing) return;
    const formData = new FormData(event.currentTarget as HTMLFormElement);
    const tokenLimit = Number(formData.get("monthly_token_limit"));
    const requestLimit = Number(formData.get("monthly_request_limit"));
    const resetAt = String(formData.get("reset_at") ?? "");
    const payload: AllowanceUpdate = {
      monthly_token_limit: Number.isFinite(tokenLimit) ? tokenLimit : null,
      monthly_request_limit: Number.isFinite(requestLimit)
        ? requestLimit
        : null,
      reset_at: resetAt ? new Date(resetAt).toISOString() : null,
    };
    setFormError("");
    try {
      await allowanceMutation.mutateAsync({ userId: editing.id, payload });
      toast("Allowance updated successfully.", "success");
      setEditing(null);
    } catch (err) {
      setFormError(
        err instanceof APIError ? err.message : "Unable to update allowance.",
      );
    }
  };

  const historyColumns: Column<{ period: string; requests: number; tokens: number }>[] = [
    { key: "period", header: "Period", render: (row) => row.period },
    { key: "requests", header: "Requests", render: (row) => formatNumber(row.requests) },
    { key: "tokens", header: "Tokens", render: (row) => formatTokens(row.tokens) },
  ];

  const userColumns: Column<AdminUsageTableRow>[] = [
    { key: "name", header: "User", render: (row) => row.name },
    { key: "tokensUsed", header: "Tokens Used", render: (row) => formatTokens(row.tokensUsed) },
    { key: "requestsUsed", header: "Requests Used", render: (row) => formatNumber(row.requestsUsed) },
    {
      key: "tokensRemaining",
      header: "Tokens Remaining",
      render: (row) => formatTokens(row.tokensRemaining),
    },
    {
      key: "resetAt",
      header: "Resets",
      render: (row) => formatRelativeTime(row.resetAt),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (row) => (
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          onClick={() => {
            setFormError("");
            setEditing(row);
          }}
        >
          <Pencil size={14} />
          Allowance
        </button>
      ),
    },
  ];

  return (
    <div className="admin-content">
      <PageHeader
        title="Usage & Token Analytics"
        subtitle="Token consumption across the platform."
      />

      <div className="admin-grid-2">
        <section className="admin-card">
          <div className="card-head">
            <h2>Usage Allowance</h2>
            <span className="card-badge">{allowance ? `${allowance.percent}%` : "—"}</span>
          </div>
          {usageLoading || !allowance || !usage ? (
            <LoadingState label="Loading usage allowance…" />
          ) : (
            <>
              <div className="detail-list">
                <div className="detail-row">
                  <span>Total Allowance</span>
                  <strong>{formatTokens(usage.monthly_token_limit)} tokens</strong>
                </div>
                <div className="detail-row">
                  <span>Used</span>
                  <strong>{formatTokens(usage.tokens_used)}</strong>
                </div>
                <div className="detail-row">
                  <span>Remaining</span>
                  <strong>{formatTokens(usage.tokens_remaining)}</strong>
                </div>
                <div className="detail-row">
                  <span>Requests</span>
                  <strong>
                    {formatNumber(usage.requests_used)} /{" "}
                    {formatNumber(usage.monthly_request_limit)}
                  </strong>
                </div>
                <div className="detail-row">
                  <span>Resets</span>
                  <strong>{formatRelativeTime(usage.reset_at)}</strong>
                </div>
              </div>
              <ProgressBar percent={allowance.percent} />
            </>
          )}
        </section>

        <section className="admin-card">
          <div className="card-head">
            <h2>Platform Totals</h2>
          </div>
          <div className="token-split">
            <div className="token-item">
              <span className="token-label">Platform Tokens</span>
              <strong className="token-value accent">
                {dashboard ? formatTokens(dashboard.total_tokens) : "—"}
              </strong>
            </div>
            <div className="token-item">
              <span className="token-label">Platform Requests</span>
              <strong className="token-value">
                {dashboard ? formatNumber(dashboard.total_requests) : "—"}
              </strong>
            </div>
            <div className="token-item">
              <span className="token-label">Active Users</span>
              <strong className="token-value">
                {dashboard ? formatNumber(dashboard.active_users) : "—"}
              </strong>
            </div>
          </div>
        </section>
      </div>

      <div className="admin-grid-2">
        <section className="admin-card">
          <div className="card-head">
            <h2>Usage History</h2>
          </div>
          {historyLoading ? (
            <LoadingState label="Loading usage history…" />
          ) : historyError ? (
            <ErrorState
              error={historyError}
              context="Unable to load usage history."
              onRetry={() => refetchHistory()}
            />
          ) : (
            <DataTable
              columns={historyColumns}
              rows={history?.items ?? []}
              rowKey={(row) => row.period}
              emptyMessage="No usage history recorded yet."
            />
          )}
        </section>

        <section className="admin-card">
          <div className="card-head">
            <h2>Usage by User</h2>
            <span className="card-badge">
              {adminUsage ? `${adminUsage.total} users` : "Loading…"}
            </span>
          </div>
          {adminLoading ? (
            <LoadingState label="Loading user usage…" />
          ) : adminError ? (
            <ErrorState
              error={adminError}
              context="Unable to load user usage."
              onRetry={() => refetchAdminUsage()}
            />
          ) : (
            <>
              <DataTable
                columns={userColumns}
                rows={(adminUsage?.items ?? []).map(toAdminUsageTableRow)}
                rowKey={(row) => row.id}
                emptyMessage="No user usage recorded yet."
              />
              <Pagination
                page={adminPage}
                pageSize={PAGE_SIZE}
                total={adminUsage?.total ?? 0}
                onPageChange={setAdminPage}
                loading={adminFetching}
              />
            </>
          )}
        </section>
      </div>

      <Modal
        open={editing !== null}
        title="Edit Usage Allowance"
        onClose={() => setEditing(null)}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setEditing(null)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="allowance-form"
              className="btn btn-primary"
              disabled={allowanceMutation.isPending}
            >
              {allowanceMutation.isPending ? "Saving…" : "Save Allowance"}
            </button>
          </>
        }
      >
        {editing && (
          <form
            id="allowance-form"
            className="modal-form"
            onSubmit={submitAllowance}
          >
            <div className="modal-warning">
              Adjusting the monthly allowance for <strong>{editing.name}</strong>{" "}
              ({editing.email}).
            </div>
            <label className="modal-field">
              <span>Monthly Token Limit</span>
              <input
                name="monthly_token_limit"
                type="number"
                min={0}
                defaultValue={editing.monthlyTokenLimit}
                required
              />
            </label>
            <label className="modal-field">
              <span>Monthly Request Limit</span>
              <input
                name="monthly_request_limit"
                type="number"
                min={0}
                defaultValue={editing.monthlyRequestLimit}
                required
              />
            </label>
            <label className="modal-field">
              <span>Reset Date</span>
              <input
                name="reset_at"
                type="date"
                defaultValue={editing.resetAt.slice(0, 10)}
              />
            </label>
            {formError && <p className="login-error">{formError}</p>}
          </form>
        )}
      </Modal>
    </div>
  );
}
