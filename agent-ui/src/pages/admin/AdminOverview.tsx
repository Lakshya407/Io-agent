import {
  Activity,
  Cpu,
  Database,
  User,
  Users,
  Webhook,
  Wrench,
  Zap,
} from "lucide-react";
import { useAdminDashboard } from "../../hooks/useAdmin";
import { useAuditLogs } from "../../hooks/useAuditLogs";
import { useReadiness } from "../../hooks/useHealth";
import { useUsage, useUsageHistory } from "../../hooks/useUsage";
import PageHeader from "../../components/admin/PageHeader";
import ProgressBar from "../../components/admin/ProgressBar";
import StatCard from "../../components/admin/StatCard";
import StatusBadge from "../../components/admin/StatusBadge";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { formatNumber, formatRelativeTime, formatTokens, usagePercent } from "../../utils/format";

const RECENT_ACTIVITY_LABELS: Record<string, string> = {
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
  USAGE_LIMIT_UPDATED: "Updated usage allowance",
  API_KEY_CREATED: "Created API key",
  API_KEY_REVOKED: "Revoked API key",
};

export default function AdminOverview() {
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useAdminDashboard();
  const { data: usage, isLoading: usageLoading } = useUsage();
  const { data: history, isLoading: historyLoading } = useUsageHistory({
    page_size: 5,
  });
  const { data: readiness } = useReadiness();
  const { data: audit, isLoading: auditLoading, error: auditError } = useAuditLogs(
    { page: 1, page_size: 5 },
  );

  const statCards = stats
    ? [
        { label: "Total Users", value: formatNumber(stats.total_users), icon: Users },
        { label: "Active Users", value: formatNumber(stats.active_users), icon: User },
        { label: "Total Requests", value: formatNumber(stats.total_requests), icon: Webhook },
        { label: "Total Tokens", value: formatTokens(stats.total_tokens), icon: Zap },
        { label: "Active Models", value: formatNumber(stats.active_models), icon: Cpu },
        { label: "Active Tools", value: formatNumber(stats.active_tools), icon: Wrench },
      ]
    : [];

  const allowance = usage
    ? {
        percent: usagePercent(usage.tokens_used, usage.monthly_token_limit),
      }
    : null;

  const maxHistoryTokens = Math.max(
    1,
    ...(history?.items.map((row) => row.tokens) ?? [1]),
  );

  return (
    <div className="admin-content">
      <PageHeader
        title="AI Agent Overview"
        subtitle="Monitor and manage the complete AI Agent platform."
      />

      {statsLoading ? (
        <LoadingState label="Loading platform statistics…" />
      ) : statsError ? (
        <ErrorState
          error={statsError}
          context="Unable to load platform statistics."
          onRetry={() => refetchStats()}
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
            <h2>Platform Usage</h2>
          </div>
          {usageLoading || !allowance || !usage ? (
            <LoadingState label="Loading usage allowance…" />
          ) : (
            <>
              <p className="allowance-summary">
                Usage Allowance — {formatTokens(usage.tokens_used)} /{" "}
                {formatTokens(usage.monthly_token_limit)} tokens
              </p>
              <div className="allowance-inline">
                <ProgressBar percent={allowance.percent} />
                <strong className="allowance-percent">
                  {allowance.percent}%
                </strong>
              </div>
              <div className="allowance-meta">
                <span>Remaining</span>
                <strong>{formatTokens(usage.tokens_remaining)} tokens</strong>
              </div>
              <div className="allowance-meta">
                <span>Requests</span>
                <strong>
                  {formatNumber(usage.requests_used)} /{" "}
                  {formatNumber(usage.monthly_request_limit)} used
                </strong>
              </div>
              <div className="allowance-meta">
                <span>Resets</span>
                <strong>{formatRelativeTime(usage.reset_at)}</strong>
              </div>
            </>
          )}
        </section>

        <section className="admin-card">
          <div className="card-head">
            <h2>Recent Token Usage</h2>
            <Database size={16} className="card-icon" />
          </div>
          {historyLoading || !history ? (
            <LoadingState label="Loading token usage…" />
          ) : history.items.length === 0 ? (
            <p className="table-empty">No token usage recorded yet.</p>
          ) : (
            <div className="breakdown-list">
              {history.items.map((row) => (
                <div className="breakdown-row" key={row.period}>
                  <div className="breakdown-head">
                    <span>{row.period}</span>
                    <strong>{formatTokens(row.tokens)} tokens</strong>
                  </div>
                  <ProgressBar
                    variant="mini"
                    percent={Math.round(
                      (row.tokens / maxHistoryTokens) * 100,
                    )}
                  />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="admin-grid-2">
        <section className="admin-card">
          <div className="card-head">
            <h2>System Status</h2>
            <Database size={16} className="card-icon" />
          </div>
          <div className="status-list">
            {readiness?.length ? (
              readiness.map((check) => (
                <div className="status-row" key={check.name}>
                  <span
                    className={`status-dot ${
                      check.status === "ok" ? "operational" : "down"
                    }`}
                  />
                  <span className="status-name">{check.name}</span>
                  <StatusBadge
                    status={check.status === "ok" ? "Operational" : "Down"}
                  />
                </div>
              ))
            ) : (
              <LoadingState label="Checking services…" />
            )}
          </div>
        </section>

        <section className="admin-card">
          <div className="card-head">
            <h2>Recent Activity</h2>
            <Activity size={16} className="card-icon" />
          </div>
          {auditError ? (
            <ErrorState error={auditError} context="Unable to load activity." />
          ) : auditLoading || !audit ? (
            <LoadingState label="Loading activity…" />
          ) : audit.items.length === 0 ? (
            <p className="table-empty">No activity recorded yet.</p>
          ) : (
            <div className="activity-feed">
              {audit.items.map((row) => (
                <div className="feed-row" key={row.id}>
                  <span className="feed-time">
                    {formatRelativeTime(row.created_at)}
                  </span>
                  <div>
                    <strong>{row.user_id ? "Admin" : "System"}</strong>
                    <small>{RECENT_ACTIVITY_LABELS[row.action] ?? row.action}</small>
                    <small className="feed-model">{row.resource_type}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
