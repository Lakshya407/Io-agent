import PageHeader from "../../components/admin/PageHeader";
import StatusBadge from "../../components/admin/StatusBadge";
import { DataTable, type Column } from "../../components/admin/DataTable";
import { agentActivity, type AgentActivityRow } from "../../data/activity";

const columns: Column<AgentActivityRow>[] = [
  { key: "timestamp", header: "Timestamp", render: (row) => row.timestamp },
  { key: "user", header: "User", render: (row) => row.user },
  { key: "action", header: "Action", render: (row) => row.action },
  { key: "tool", header: "Tool", render: (row) => row.tool },
  { key: "model", header: "Model", render: (row) => row.model },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusBadge status={row.status} />,
  },
];

export default function AdminActivity() {
  return (
    <div className="admin-content">
      <PageHeader
        title="Agent Activity"
        subtitle="Live record of agent actions across the platform."
      />

      <section className="admin-card">
        <div className="card-head">
          <h2>Activity Feed</h2>
          <span className="mock-note">Mock data</span>
        </div>
        <DataTable
          columns={columns}
          rows={agentActivity}
          rowKey={(row) => row.id}
        />
      </section>
    </div>
  );
}
