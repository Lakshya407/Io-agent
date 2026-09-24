import {
  Activity,
  AlertTriangle,
  Clock,
  Coins,
  Cpu,
  Pencil,
  Users,
  Zap,
} from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import BarChart from "../../components/admin/BarChart";
import { DataTable, type Column } from "../../components/admin/DataTable";
import FilterBar from "../../components/admin/FilterBar";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import Pagination from "../../components/admin/Pagination";
import ProgressBar from "../../components/admin/ProgressBar";
import StatCard from "../../components/admin/StatCard";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import {
  useAdminDashboard,
  useAdminUsage,
  useAdminUsageModels,
  useAdminUsageSummary,
  useAdminUsageTimeline,
  useAdminUsageUsers,
  useUpdateAllowance,
  useUsageForUser,
} from "../../hooks/useAdmin";
import { useModels } from "../../hooks/useModels";
import { useUsage, useUsageHistory } from "../../hooks/useUsage";
import { useUsers } from "../../hooks/useUsers";
import { APIError } from "../../types/common";
import type {
  AdminModelUsageRow,
  AdminUserUsageRow,
  AllowanceUpdate,
  UsageFilterParams,
} from "../../types/usage";
import {
  toAdminUsageTableRow,
  type AdminUsageTableRow,
} from "../../utils/adapters";
import {
  formatLatency,
  formatNumber,
  formatRelativeTime,
  formatTokens,
  successRate,
  usagePercent,
} from "../../utils/format";

const PAGE_SIZE = 20;

/** Range presets understood by `resolve_period` on the backend. */
const RANGE_OPTIONS = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "custom", label: "Custom" },
];

export default function AdminUsage() {
  // --- filters -----------------------------------------------------------
  const [range, setRange] = useState("");
  const [model, setModel] = useState("");
  const [userId, setUserId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const isCustom = range === "custom";

  // Explicit dates always win server-side, so `custom` simply omits `range`.
  const filterParams: UsageFilterParams = useMemo(() => {
    const params: UsageFilterParams = {};
    if (isCustom) {
      if (dateFrom) params.date_from = `${dateFrom}T00:00:00Z`;
      if (dateTo) params.date_to = `${dateTo}T00:00:00Z`;
    } else if (range) {
      params.range = range;
    }
    if (model) params.model = model;
    if (userId) params.user_id = userId;
    return params;
  }, [range, isCustom, dateFrom, dateTo, model, userId]);

  // --- analytics ---------------------------------------------------------
  const summary = useAdminUsageSummary(filterParams);
  const timeline = useAdminUsageTimeline(filterParams);
  const modelUsage = useAdminUsageModels(filterParams);
  const topUsers = useAdminUsageUsers(filterParams);

  // Filter option sources (not filtered themselves).
  const { data: modelCatalog } = useModels({ activeOnly: false });
  const { data: userCatalog } = useUsers({ page: 1, page_size: 100 });

  // --- retained sections -------------------------------------------------
  const { data: usage, isLoading: usageLoading } = useUsage();
  const {
    data: history,
    isLoading: historyLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useUsageHistory({ page_size: 10 });
  const { data: dashboard } = useAdminDashboard();
  const [adminPage, setAdminPage] = useState(1);
  const {
    data: adminUsage,
    isLoading: adminLoading,
    error: adminError,
    refetch: refetchAdminUsage,
    isFetching: adminFetching,
  } = useAdminUsage({ page: adminPage, page_size: PAGE_SIZE });

  // --- allowance editor --------------------------------------------------
  const [editing, setEditing] = useState<AdminUsageTableRow | null>(null);
  const [formError, setFormError] = useState("");
  const allowanceMutation = useUpdateAllowance();
  const allowanceDetail = useUsageForUser(editing?.id ?? null);
  const { toast } = useToast();

  const summaryData = summary.data;
  const statCards = [
    {
      label: "Total Requests",
      value: summaryData ? formatNumber(summaryData.total_requests) : "—",
      icon: Activity,
    },
    {
      label: "Failed Requests",
      value: summaryData ? formatNumber(summaryData.failed_requests) : "—",
      icon: AlertTriangle,
    },
    {
      label: "Total Tokens",
      value: summaryData ? formatTokens(summaryData.total_tokens) : "—",
      icon: Coins,
    },
    {
      label: "Input Tokens",
      value: summaryData ? formatTokens(summaryData.prompt_tokens) : "—",
      icon: Zap,
    },
    {
      label: "Output Tokens",
      value: summaryData ? formatTokens(summaryData.completion_tokens) : "—",
      icon: Cpu,
    },
    {
      label: "Active Users",
      value: summaryData ? formatNumber(summaryData.active_users) : "—",
      icon: Users,
    },
    {
      label: "Avg Response Time",
      value: formatLatency(summaryData?.average_response_time_ms ?? null),
      icon: Clock,
    },
  ];

  // The timeline arrives newest-first; reverse it, then keep the last month.
  const chartData = useMemo(() => {
    const points = [...(timeline.data ?? [])].reverse().slice(-31);
    return points.map((point) => ({
      label: String(point.period).slice(5),
      value: point.total_tokens,
      display: formatTokens(point.total_tokens),
    }));
  }, [timeline.data]);

  const modelOptions = useMemo(
    () =>
      (modelCatalog?.items ?? []).map((item) => ({
        value: item.name,
        label: item.name,
      })),
    [modelCatalog],
  );

  const userOptions = useMemo(
    () =>
      (userCatalog?.items ?? []).map((item) => ({
        value: item.id,
        label: item.name || item.email,
      })),
    [userCatalog],
  );

  const historyColumns: Column<{
    period: string;
    requests: number;
    tokens: number;
  }>[] = [
    { key: "period", header: "Period", render: (row) => row.period },
    {
      key: "requests",
      header: "Requests",
      render: (row) => formatNumber(row.requests),
    },
    { key: "tokens", header: "Tokens", render: (row) => formatTokens(row.tokens) },
  ];

  const modelColumns: Column<AdminModelUsageRow>[] = [
    { key: "model", header: "Model", render: (row) => row.model },
    { key: "provider", header: "Provider", render: (row) => row.provider ?? "—" },
    {
      key: "requests",
      header: "Requests",
      render: (row) => formatNumber(row.requests),
    },
    {
      key: "tokens",
      header: "Tokens",
      render: (row) => formatTokens(row.total_tokens),
    },
    {
      key: "prompt",
      header: "Input",
      render: (row) => formatTokens(row.prompt_tokens),
    },
    {
      key: "completion",
      header: "Output",
      render: (row) => formatTokens(row.completion_tokens),
    },
    {
      key: "latency",
      header: "Avg",
      render: (row) => formatLatency(row.average_response_time_ms),
    },
  ];

  const topUserColumns: Column<AdminUserUsageRow>[] = [
    {
      key: "name",
      header: "User",
      render: (row) => row.name || row.email,
    },
    {
      key: "requests",
      header: "Requests",
      render: (row) => formatNumber(row.requests),
    },
    {
      key: "tokens",
      header: "Tokens",
      render: (row) => formatTokens(row.total_tokens),
    },
    {
      key: "success",
      header: "Success",
      render: (row) => successRate(row.successful_requests, row.requests),
    },
    {
      key: "latency",
      header: "Avg",
      render: (row) => formatLatency(row.average_response_time_ms),
    },
  ];

  const userColumns: Column<AdminUsageTableRow>[] = [
    { key: "name", header: "User", render: (row) => row.name },
    {
      key: "tokensUsed",
      header: "Tokens Used",
      render: (row) => formatTokens(row.tokensUsed),
    },
    {
      key: "requestsUsed",
      header: "Requests Used",
      render: (row) => formatNumber(row.requestsUsed),
    },
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

    // Daily limits and the enabled flag only arrive with the per-user detail
    // fetch. If that fetch failed we leave them untouched rather than
    // accidentally clearing limits the admin never edited.
    const detail = allowanceDetail.data;
    if (detail) {
      const dailyTokens = String(
        formData.get("daily_token_limit") ?? "",
      ).trim();
      const dailyRequests = String(
        formData.get("daily_request_limit") ?? "",
      ).trim();
      payload.daily_token_limit =
        dailyTokens === "" ? null : Number(dailyTokens);
      payload.daily_request_limit =
        dailyRequests === "" ? null : Number(dailyRequests);
      payload.is_enabled = formData.get("is_enabled") === "on";
    }

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

  const detail = allowanceDetail.data;

  return (
    <div className="admin-content">
      <PageHeader
        title="Usage & Token Analytics"
        subtitle="Token consumption across the platform."
      />

      <FilterBar
        filters={[
          {
            label: "Range",
            value: range,
            options: RANGE_OPTIONS,
            onChange: setRange,
          },
          {
            label: "Model",
            value: model,
            options: modelOptions,
            onChange: setModel,
          },
          {
            label: "User",
            value: userId,
            options: userOptions,
            onChange: setUserId,
          },
        ]}
        dateValue={dateFrom}
        onDateChange={isCustom ? setDateFrom : undefined}
        dateToValue={dateTo}
        onDateToChange={isCustom ? setDateTo : undefined}
      />

      {summary.isLoading ? (
        <LoadingState label="Loading usage summary…" />
      ) : summary.error ? (
        <ErrorState
          error={summary.error}
          context="Unable to load the usage summary."
          onRetry={() => summary.refetch()}
        />
      ) : (
        <div className="stat-grid">
          {statCards.map((card) => (
            <StatCard
              key={card.label}
              label={card.label}
              value={card.value}
              icon={card.icon}
            />
          ))}
        </div>
      )}

      <div className="admin-grid-2">
        <section className="admin-card">
          <div className="card-head">
            <h2>Tokens Over Time</h2>
            <span className="card-badge">
              {timeline.data ? `${chartData.length} days` : "Loading…"}
            </span>
          </div>
          {timeline.isLoading ? (
            <LoadingState label="Loading timeline…" />
          ) : timeline.error ? (
            <ErrorState
              error={timeline.error}
              context="Unable to load the usage timeline."
              onRetry={() => timeline.refetch()}
            />
          ) : chartData.length === 0 ? (
            <div className="table-empty">No usage recorded in this period.</div>
          ) : (
            <BarChart data={chartData} />
          )}
        </section>

        <section className="admin-card">
          <div className="card-head">
            <h2>Usage by Model</h2>
            <span className="card-badge">
              {modelUsage.data ? `${modelUsage.data.length} models` : "Loading…"}
            </span>
          </div>
          {modelUsage.isLoading ? (
            <LoadingState label="Loading model usage…" />
          ) : modelUsage.error ? (
            <ErrorState
              error={modelUsage.error}
              context="Unable to load per-model usage."
              onRetry={() => modelUsage.refetch()}
            />
          ) : (
            <DataTable
              columns={modelColumns}
              rows={modelUsage.data ?? []}
              rowKey={(row) => row.model}
              emptyMessage="No usage recorded for this period."
            />
          )}
        </section>
      </div>

      <div className="admin-grid-2">
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

        <section className="admin-card">
          <div className="card-head">
            <h2>Top Users</h2>
            <span className="card-badge">
              {topUsers.data ? `${topUsers.data.length} users` : "Loading…"}
            </span>
          </div>
          {topUsers.isLoading ? (
            <LoadingState label="Loading top users…" />
          ) : topUsers.error ? (
            <ErrorState
              error={topUsers.error}
              context="Unable to load per-user usage."
              onRetry={() => topUsers.refetch()}
            />
          ) : (
            <DataTable
              columns={topUserColumns}
              rows={(topUsers.data ?? []).slice(0, 8)}
              rowKey={(row) => row.user_id}
              emptyMessage="No usage recorded for this period."
            />
          )}
        </section>
      </div>

      <div className="admin-grid-2">
        <section className="admin-card">
          <div className="card-head">
            <h2>Usage Allowance</h2>
            <span className="card-badge">
              {usage ? `${usagePercent(usage.tokens_used, usage.monthly_token_limit)}%` : "—"}
            </span>
          </div>
          {usageLoading || !usage ? (
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
              <ProgressBar
                percent={usagePercent(usage.tokens_used, usage.monthly_token_limit)}
              />
            </>
          )}
        </section>

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
      </div>

      <section className="admin-card">
        <div className="card-head">
          <h2>Allowances by User</h2>
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
        {editing &&
          (allowanceDetail.isLoading || (!detail && !allowanceDetail.error) ? (
            <LoadingState label="Loading allowance…" />
          ) : (
            <form
              id="allowance-form"
              className="modal-form"
              onSubmit={submitAllowance}
            >
              <div className="modal-warning">
                Adjusting the allowance for <strong>{editing.name}</strong> (
                {editing.email}). An empty daily limit means unlimited.
              </div>
              <div className="modal-field-row">
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
              </div>
              <div className="modal-field-row">
                <label className="modal-field">
                  <span>Daily Token Limit</span>
                  <input
                    name="daily_token_limit"
                    type="number"
                    min={0}
                    placeholder="Unlimited"
                    defaultValue={detail?.daily_token_limit ?? ""}
                  />
                </label>
                <label className="modal-field">
                  <span>Daily Request Limit</span>
                  <input
                    name="daily_request_limit"
                    type="number"
                    min={0}
                    placeholder="Unlimited"
                    defaultValue={detail?.daily_request_limit ?? ""}
                  />
                </label>
              </div>
              <label className="modal-field">
                <span>Reset Date</span>
                <input
                  name="reset_at"
                  type="date"
                  defaultValue={editing.resetAt.slice(0, 10)}
                />
              </label>
              <label className="remember">
                <input
                  type="checkbox"
                  name="is_enabled"
                  defaultChecked={detail?.is_enabled ?? true}
                />
                Allowance enabled (uncheck to block this user entirely)
              </label>
              {formError && <p className="login-error">{formError}</p>}
            </form>
          ))}
      </Modal>
    </div>
  );
}
