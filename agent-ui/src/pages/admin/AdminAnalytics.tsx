import { BarChart3, TrendingUp, User, Users } from "lucide-react";
import { useMemo, useState } from "react";
import BarChart from "../../components/admin/BarChart";
import { DataTable, type Column } from "../../components/admin/DataTable";
import FilterBar from "../../components/admin/FilterBar";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import {
  useAdminUsageSummary,
  useAdminUsageTimeline,
  useAdminUsageUsers,
} from "../../hooks/useAdmin";
import { useUsers } from "../../hooks/useUsers";
import type { AdminUserUsageRow, UsageFilterParams } from "../../types/usage";
import {
  formatLatency,
  formatNumber,
  formatTokens,
  successRate,
} from "../../utils/format";

const RANGE_OPTIONS = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

export default function AdminAnalytics() {
  const [range, setRange] = useState("");

  const filterParams: UsageFilterParams = useMemo(
    () => (range ? { range } : {}),
    [range],
  );

  const summary = useAdminUsageSummary(filterParams);
  const timeline = useAdminUsageTimeline(filterParams);
  const topUsers = useAdminUsageUsers(filterParams);
  // Total account count is independent of the usage period.
  const { data: allUsers } = useUsers({ page: 1, page_size: 1 });

  const data = summary.data;
  const activeUsers = data?.active_users ?? 0;
  const avgTokensPerUser =
    data && activeUsers > 0
      ? `${formatTokens(Math.round(data.total_tokens / activeUsers))}`
      : "—";

  const statCards = [
    {
      label: "Total Users",
      value: allUsers ? formatNumber(allUsers.total) : "—",
      icon: Users,
    },
    {
      label: "Active Users",
      value: data ? formatNumber(activeUsers) : "—",
      icon: User,
    },
    {
      label: "Total Requests",
      value: data ? formatNumber(data.total_requests) : "—",
      icon: BarChart3,
    },
    {
      label: "Avg Tokens / Active User",
      value: avgTokensPerUser,
      icon: TrendingUp,
    },
  ];

  // Timeline arrives newest-first; reverse for the chart and cap at a month.
  const chartData = useMemo(() => {
    const points = [...(timeline.data ?? [])].reverse().slice(-31);
    return points.map((point) => ({
      label: String(point.period).slice(5),
      value: point.requests,
      display: formatNumber(point.requests),
    }));
  }, [timeline.data]);

  const columns: Column<AdminUserUsageRow>[] = [
    {
      key: "user",
      header: "User",
      render: (row) => row.name || row.email,
    },
    {
      key: "tokens",
      header: "Tokens",
      render: (row) => formatTokens(row.total_tokens),
    },
    {
      key: "requests",
      header: "Requests",
      render: (row) => formatNumber(row.requests),
    },
    {
      key: "successRate",
      header: "Success Rate",
      render: (row) => successRate(row.successful_requests, row.requests),
    },
    {
      key: "avgResponseTime",
      header: "Avg Response Time",
      render: (row) => formatLatency(row.average_response_time_ms),
    },
  ];

  return (
    <div className="admin-content">
      <PageHeader
        title="User Analytics"
        subtitle="Engagement and usage across the platform."
      />

      <FilterBar
        filters={[
          { label: "Range", value: range, options: RANGE_OPTIONS, onChange: setRange },
        ]}
      />

      {summary.isLoading ? (
        <LoadingState label="Loading analytics…" />
      ) : summary.error ? (
        <ErrorState
          error={summary.error}
          context="Unable to load analytics."
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

      <section className="admin-card">
        <div className="card-head">
          <h2>Requests Per Day</h2>
          <TrendingUp size={16} className="card-icon" />
        </div>
        {timeline.isLoading ? (
          <LoadingState label="Loading timeline…" />
        ) : timeline.error ? (
          <ErrorState
            error={timeline.error}
            context="Unable to load the requests timeline."
            onRetry={() => timeline.refetch()}
          />
        ) : chartData.length === 0 ? (
          <div className="table-empty">No requests recorded in this period.</div>
        ) : (
          <BarChart data={chartData} />
        )}
      </section>

      <section className="admin-card">
        <div className="card-head">
          <h2>Top Users by Token Usage</h2>
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
            columns={columns}
            rows={topUsers.data ?? []}
            rowKey={(row) => row.user_id}
            emptyMessage="No usage recorded for this period."
          />
        )}
      </section>
    </div>
  );
}
