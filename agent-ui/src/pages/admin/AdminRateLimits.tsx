import { Gauge, Pencil, Plus, Shield } from "lucide-react";
import { useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import StatusBadge from "../../components/admin/StatusBadge";
import {
  rateLimitActionOptions,
  rateLimitRules as initialRules,
  rateLimitStats,
  rateLimitWindowOptions,
  type RateLimitRule,
} from "../../data/rateLimits";

const statCards = [
  {
    label: "Requests Today",
    value: rateLimitStats.requestsToday,
    icon: Gauge,
  },
  {
    label: "Requests Blocked",
    value: rateLimitStats.requestsBlocked,
    icon: Shield,
  },
  {
    label: "Rate Limit Violations",
    value: rateLimitStats.violations,
    icon: Shield,
  },
];

const emptyForm = {
  scope: "",
  limit: 100,
  window: rateLimitWindowOptions[1],
  action: rateLimitActionOptions[0],
  status: "Active" as RateLimitRule["status"],
};

export default function AdminRateLimits() {
  const [rules, setRules] = useState<RateLimitRule[]>(initialRules);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RateLimitRule | null>(null);
  const [form, setForm] = useState(emptyForm);

  const toggleStatus = (id: string) => {
    setRules((current) =>
      current.map((rule) =>
        rule.id === id
          ? { ...rule, status: rule.status === "Active" ? "Inactive" : "Active" }
          : rule,
      ),
    );
  };

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (rule: RateLimitRule) => {
    setEditing(rule);
    setForm({
      scope: rule.scope,
      limit: rule.limit,
      window: rule.window,
      action: rule.action,
      status: rule.status,
    });
    setModalOpen(true);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!form.scope.trim()) return;
    if (editing) {
      setRules((current) =>
        current.map((rule) =>
          rule.id === editing.id
            ? {
                ...rule,
                scope: form.scope.trim(),
                limit: form.limit,
                window: form.window,
                action: form.action,
                status: form.status,
              }
            : rule,
        ),
      );
    } else {
      setRules((current) => [
        ...current,
        {
          id: `rl${Date.now()}`,
          scope: form.scope.trim(),
          limit: form.limit,
          window: form.window,
          action: form.action,
          status: form.status,
        },
      ]);
    }
    setModalOpen(false);
  };

  const columns: Column<RateLimitRule>[] = [
    { key: "scope", header: "Scope", render: (row) => row.scope },
    {
      key: "limit",
      header: "Limit",
      render: (row) => `${row.limit.toLocaleString()} requests`,
    },
    { key: "window", header: "Window", render: (row) => row.window },
    { key: "action", header: "Action", render: (row) => row.action },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <button
          type="button"
          className={`pill toggle-pill ${row.status.toLowerCase()}`}
          onClick={() => toggleStatus(row.id)}
          aria-pressed={row.status === "Active"}
          title="Toggle rule"
        >
          {row.status}
        </button>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (row) => (
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          onClick={() => openEdit(row)}
        >
          <Pencil size={14} />
          Edit
        </button>
      ),
    },
  ];

  return (
    <div className="admin-content">
      <PageHeader
        title="Rate Limiting"
        subtitle="Control usage limits for users, APIs and models."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={openCreate}
          >
            <Plus size={15} />
            Add Rule
          </button>
        }
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
          <h2>Rate Limit Rules</h2>
          <span className="card-badge">{rules.length} rules</span>
        </div>
        <DataTable columns={columns} rows={rules} rowKey={(row) => row.id} />
      </section>

      <Modal
        open={modalOpen}
        title={editing ? "Edit Rate Limit Rule" : "Add Rate Limit Rule"}
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="rate-limit-form"
              className="btn btn-primary"
            >
              {editing ? "Save Changes" : "Add Rule"}
            </button>
          </>
        }
      >
        <form
          id="rate-limit-form"
          className="modal-form"
          onSubmit={handleSubmit}
        >
          <label className="modal-field">
            <span>Scope</span>
            <input
              required
              value={form.scope}
              onChange={(event) =>
                setForm((current) => ({ ...current, scope: event.target.value }))
              }
              placeholder="e.g. All Users"
            />
          </label>
          <label className="modal-field">
            <span>Limit (requests)</span>
            <input
              type="number"
              min={1}
              required
              value={form.limit}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  limit: Number(event.target.value),
                }))
              }
            />
          </label>
          <label className="modal-field">
            <span>Time Window</span>
            <select
              className="select"
              value={form.window}
              onChange={(event) =>
                setForm((current) => ({ ...current, window: event.target.value }))
              }
            >
              {rateLimitWindowOptions.map((window) => (
                <option key={window} value={window}>
                  {window}
                </option>
              ))}
            </select>
          </label>
          <label className="modal-field">
            <span>Action</span>
            <select
              className="select"
              value={form.action}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  action: event.target.value,
                }))
              }
            >
              {rateLimitActionOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="modal-field">
            <span>Status</span>
            <select
              className="select"
              value={form.status}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  status: event.target.value as RateLimitRule["status"],
                }))
              }
            >
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </label>
        </form>
      </Modal>
    </div>
  );
}
