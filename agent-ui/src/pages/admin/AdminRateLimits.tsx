import { Gauge, Pencil, Plus, Shield, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import {
  useCreateRateLimitRule,
  useDeleteRateLimitRule,
  useRateLimitRules,
  useRateLimitStats,
  useUpdateRateLimitRule,
} from "../../hooks/useRateLimits";
import { APIError } from "../../types/common";
import type { RateLimitRule, RateLimitScope } from "../../types/rateLimit";
import { formatNumber } from "../../utils/format";

const SCOPES: RateLimitScope[] = ["all", "user", "ip"];

/** Common window presets (seconds) offered in the rule editor. */
const WINDOW_OPTIONS = [
  { value: 60, label: "1 minute" },
  { value: 300, label: "5 minutes" },
  { value: 900, label: "15 minutes" },
  { value: 3600, label: "1 hour" },
  { value: 86400, label: "1 day" },
  { value: 604800, label: "1 week" },
];

/** Human label for a window, falling back to the raw second count. */
function windowLabel(seconds: number): string {
  return (
    WINDOW_OPTIONS.find((option) => option.value === seconds)?.label ??
    `${formatNumber(seconds)} s`
  );
}

const emptyForm = {
  scope: "all" as RateLimitScope,
  limit: 60,
  windowSeconds: 3600,
  isActive: true,
};

export default function AdminRateLimits() {
  const { data: rules, isLoading, error, refetch } = useRateLimitRules();
  const { data: stats } = useRateLimitStats();
  const createMutation = useCreateRateLimitRule();
  const updateMutation = useUpdateRateLimitRule();
  const deleteMutation = useDeleteRateLimitRule();
  const { toast } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RateLimitRule | null>(null);
  const [deleting, setDeleting] = useState<RateLimitRule | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState("");

  const list = rules ?? [];

  const statCards = [
    {
      label: "Requests Checked (today)",
      value: stats ? formatNumber(stats.checked) : "—",
      icon: Gauge,
    },
    {
      label: "Requests Blocked (today)",
      value: stats ? formatNumber(stats.blocked) : "—",
      icon: Shield,
    },
    {
      label: "Violations (today)",
      value: stats ? formatNumber(stats.violations) : "—",
      icon: Shield,
    },
  ];

  const openCreate = () => {
    setFormError("");
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (rule: RateLimitRule) => {
    setFormError("");
    setEditing(rule);
    setForm({
      scope: rule.scope,
      limit: rule.limit,
      windowSeconds: rule.window_seconds,
      isActive: rule.is_active,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError("");
    try {
      if (editing) {
        await updateMutation.mutateAsync({
          ruleId: editing.id,
          payload: {
            scope: form.scope,
            limit: form.limit,
            window_seconds: form.windowSeconds,
            is_active: form.isActive,
          },
        });
        toast("Rate limit rule updated.", "success");
      } else {
        await createMutation.mutateAsync({
          scope: form.scope,
          limit: form.limit,
          window_seconds: form.windowSeconds,
          is_active: form.isActive,
        });
        toast("Rate limit rule created.", "success");
      }
      setModalOpen(false);
    } catch (err) {
      setFormError(
        err instanceof APIError ? err.message : "Unable to save the rule.",
      );
    }
  };

  const toggleStatus = async (rule: RateLimitRule) => {
    try {
      await updateMutation.mutateAsync({
        ruleId: rule.id,
        payload: { is_active: !rule.is_active },
      });
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to update the rule.",
        "error",
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      toast("Rate limit rule deleted.", "success");
      setDeleting(null);
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to delete the rule.",
        "error",
      );
    }
  };

  const columns: Column<RateLimitRule>[] = [
    { key: "scope", header: "Scope", render: (row) => row.scope },
    {
      key: "limit",
      header: "Limit",
      render: (row) => `${formatNumber(row.limit)} requests`,
    },
    {
      key: "window",
      header: "Window",
      render: (row) => windowLabel(row.window_seconds),
    },
    { key: "action", header: "Action", render: (row) => row.action },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <button
          type="button"
          className={`pill toggle-pill ${row.is_active ? "active" : "inactive"}`}
          onClick={() => void toggleStatus(row)}
          disabled={updateMutation.isPending}
          aria-pressed={row.is_active}
          title="Toggle rule"
        >
          {row.is_active ? "Active" : "Inactive"}
        </button>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (row) => (
        <div className="row-actions">
          <button
            type="button"
            className="btn-action"
            onClick={() => openEdit(row)}
            aria-label="Edit rate limit rule"
            title="Edit"
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="btn-action danger"
            onClick={() => setDeleting(row)}
            aria-label="Delete rate limit rule"
            title="Delete"
          >
            <Trash2 size={15} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="admin-content">
      <PageHeader
        title="Rate Limiting"
        subtitle="Control usage limits for users, APIs and models."
        actions={
          <button type="button" className="btn btn-primary" onClick={openCreate}>
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
          <span className="card-badge">
            {rules ? `${list.length} rules` : "Loading…"}
          </span>
        </div>
        {isLoading ? (
          <LoadingState label="Loading rate limit rules…" />
        ) : error ? (
          <ErrorState
            error={error}
            context="Unable to load rate limit rules."
            onRetry={() => refetch()}
          />
        ) : (
          <>
            <DataTable
              columns={columns}
              rows={list}
              rowKey={(row) => row.id}
              emptyMessage="No custom rules configured."
            />
            {list.length === 0 && (
              <p className="modal-warning" style={{ marginTop: 12 }}>
                While no rules exist, the built-in per-minute and per-hour
                defaults from the server configuration are enforced instead.
              </p>
            )}
          </>
        )}
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
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Saving…"
                : editing
                  ? "Save Changes"
                  : "Add Rule"}
            </button>
          </>
        }
      >
        <form
          id="rate-limit-form"
          className="modal-form"
          onSubmit={handleSubmit}
        >
          <div className="modal-field-row">
            <label className="modal-field">
              <span>Scope</span>
              <select
                className="select"
                value={form.scope}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    scope: event.target.value as RateLimitScope,
                  }))
                }
              >
                {SCOPES.map((scope) => (
                  <option key={scope} value={scope}>
                    {scope}
                  </option>
                ))}
              </select>
            </label>
            <label className="modal-field">
              <span>Action</span>
              <select className="select" value="block" disabled>
                <option value="block">block</option>
              </select>
            </label>
          </div>
          <div className="modal-field-row">
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
                value={form.windowSeconds}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    windowSeconds: Number(event.target.value),
                  }))
                }
              >
                {WINDOW_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="remember">
            <input
              type="checkbox"
              checked={form.isActive}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  isActive: event.target.checked,
                }))
              }
            />
            Rule active
          </label>
          <p className="modal-warning">
            Exceeding the limit blocks the request with a 429 response.
          </p>
          {formError && <p className="login-error">{formError}</p>}
        </form>
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete Rate Limit Rule"
        size="sm"
        onClose={() => setDeleting(null)}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setDeleting(null)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
            >
              <Trash2 size={15} />
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </button>
          </>
        }
      >
        {deleting && (
          <p className="modal-warning">
            Delete the <strong>{deleting.scope}</strong> rule (
            {formatNumber(deleting.limit)} per {windowLabel(deleting.window_seconds)
            })? This cannot be undone.
          </p>
        )}
      </Modal>
    </div>
  );
}
