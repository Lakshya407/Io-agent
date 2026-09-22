import { BarChart3, TrendingUp, User, Users } from "lucide-react";
import BarChart from "../../components/admin/BarChart";
import { DataTable, type Column } from "../../components/admin/DataTable";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import {
  analyticsStats,
  dailyActiveUsers,
  topUsers,
  type TopUserRow,
} from "../../data/users";

const statCards = [
  {
    label: "Daily Active Users",
    value: String(analyticsStats.dailyActive),
    icon: User,
  },
  {
    label: "Monthly Active Users",
    value: String(analyticsStats.monthlyActive),
    icon: Users,
  },
  {
    label: "Total Users",
    value: String(analyticsStats.totalUsers),
    icon: Users,
  },
  {
    label: "Avg Conversations/User",
    value: analyticsStats.avgConversationsPerUser,
    icon: BarChart3,
  },
];

const columns: Column<TopUserRow>[] = [
  { key: "user", header: "User", render: (row) => row.user },
  { key: "tokens", header: "Tokens", render: (row) => row.tokens },
  {
    key: "conversations",
    header: "Conversations",
    render: (row) => row.conversations,
  },
];

export default function AdminAnalytics() {
  return (
    <div className="admin-content">
      <PageHeader
        title="User Analytics"
        subtitle="Engagement and usage across the platform."
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
          <h2>Daily Active Users</h2>
          <TrendingUp size={16} className="card-icon" />
        </div>
        <BarChart
          data={dailyActiveUsers.map((row) => ({
            label: row.day,
            value: row.users,
            display: String(row.users),
          }))}
        />
      </section>

      <section className="admin-card">
        <div className="card-head">
          <h2>Top Users by Token Usage</h2>
        </div>
        <DataTable
          columns={columns}
          rows={topUsers}
          rowKey={(row) => row.user}
        />
      </section>
    </div>
  );
}
