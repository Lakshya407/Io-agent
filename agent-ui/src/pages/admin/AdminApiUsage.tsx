import { Activity, CheckCircle2, Clock, XCircle } from "lucide-react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import FilterBar from "../../components/admin/FilterBar";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useAdminUsageModels, useAdminUsageSummary } from "../../hooks/useAdmin";
import { useMemo, useState } from "react";
import type { AdminModelUsageRow, UsageFilterParams } from "../../types/usage";
import { formatLatency, formatNumber, formatTokens, successRate } from "../../utils/format";

const RANGE_OPTIONS = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

export default function AdminApiUsage() {
  const [range, setRange] = useState("");

  const filterParams: UsageFilterParams = useMemo(
    () => (range ? { range } : {}),
    [range],
  );

  const summary = useAdminUsageSummary(filterParams);
  const models = useAdminUsageModels(filterParams);

  const data = summary.data;
  const statCards = [
    {
      label: "Total API Requests",
      value: data ? formatNumber(data.total_requests) : "—",
      icon: Activity,
    },
    {
      label: "Successful Requests",
      value: data ? formatNumber(data.successful_requests) : "—",
      icon: CheckCircle2,
    },
    {
      label: "Failed Requests",
      value: data ? formatNumber(data.failed_requests) : "—",
      icon: XCircle,
    },
    {
      label: "Average Response Time",
      value: formatLatency(data?.average_response_time_ms ?? null),
      icon: Clock,
    },
  ];

  const columns: Column<AdminModelUsageRow>[] = [
    { key: "model", header: "Model", render: (row) => row.model },
    { key: "provider", header: "Provider", render: (row) => row.provider ?? "—" },
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
      key: "failed",
      header: "Failed",
      render: (row) => formatNumber(row.failed_requests),
    },
    {
      key: "avgResponseTime",
      header: "Avg Response Time",
      render: (row) => formatLatency(row.average_response_time_ms),
    },
    {
      key: "tokens",
      header: "Tokens",
      render: (row) => formatTokens(row.total_tokens),
    },
  ];

  return (
    <div className="admin-content">
      <PageHeader
        title="API Usage"
        subtitle="Request volume and reliability per model."
      />

      <FilterBar
        filters={[
          { label: "Range", value: range, options: RANGE_OPTIONS, onChange: setRange },
        ]}
      />

      {summary.isLoading ? (
        <LoadingState label="Loading request statistics…" />
      ) : summary.error ? (
        <ErrorState
          error={summary.error}
          context="Unable to load request statistics."
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
          <h2>Reliability by Model</h2>
          <span className="card-badge">
            {models.data ? `${models.data.length} models` : "Loading…"}
          </span>
        </div>
        {models.isLoading ? (
          <LoadingState label="Loading reliability data…" />
        ) : models.error ? (
          <ErrorState
            error={models.error}
            context="Unable to load per-model reliability."
            onRetry={() => models.refetch()}
          />
        ) : (
          <DataTable
            columns={columns}
            rows={models.data ?? []}
            rowKey={(row) => row.model}
            emptyMessage="No requests recorded for this period."
          />
        )}
      </section>
    </div>
  );
}
