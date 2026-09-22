import { Activity, CheckCircle2, Clock, XCircle } from "lucide-react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import StatusBadge from "../../components/admin/StatusBadge";
import { apiUsage, apiUsageStats, type ApiUsageRow } from "../../data/apiUsage";

const statCards = [
  {
    label: "Total API Requests",
    value: apiUsageStats.totalRequests,
    icon: Activity,
  },
  {
    label: "Successful Requests",
    value: apiUsageStats.successfulRequests,
    icon: CheckCircle2,
  },
  {
    label: "Failed Requests",
    value: apiUsageStats.failedRequests,
    icon: XCircle,
  },
  {
    label: "Average Response Time",
    value: apiUsageStats.avgResponseTime,
    icon: Clock,
  },
];

const columns: Column<ApiUsageRow>[] = [
  { key: "api", header: "API", render: (row) => row.api },
  { key: "requests", header: "Requests", render: (row) => row.requests },
  { key: "tokens", header: "Tokens", render: (row) => row.tokens },
  {
    key: "successRate",
    header: "Success Rate",
    render: (row) => row.successRate,
  },
  {
    key: "avgResponseTime",
    header: "Avg Response Time",
    render: (row) => row.avgResponseTime,
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusBadge status={row.status} />,
  },
];

export default function AdminApiUsage() {
  return (
    <div className="admin-content">
      <PageHeader
        title="API Usage"
        subtitle="Request volume and reliability per API endpoint."
      />

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

      <section className="admin-card">
        <div className="card-head">
          <h2>API Endpoints</h2>
        </div>
        <DataTable
          columns={columns}
          rows={apiUsage}
          rowKey={(row) => row.api}
        />
      </section>
    </div>
  );
}
