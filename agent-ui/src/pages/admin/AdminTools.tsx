import { Pencil, Plus, Trash2, Wrench } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import { useAdminDashboard } from "../../hooks/useAdmin";
import {
  useCreateTool,
  useDeleteTool,
  useTools,
  useToggleToolStatus,
  useUpdateTool,
} from "../../hooks/useTools";
import { toToolRow, type ToolRow } from "../../utils/adapters";
import { APIError } from "../../types/common";
import type { ToolType } from "../../types/tool";

const CATEGORIES: ToolType[] = [
  "search",
  "knowledge",
  "utility",
  "development",
  "analytics",
  "media",
];

const emptyForm = {
  name: "",
  description: "",
  type: "utility" as ToolType,
  is_active: true,
};

export default function AdminTools() {
  const { data, isLoading, error, refetch } = useTools({ activeOnly: false });
  const { data: dashboard } = useAdminDashboard();
  const createMutation = useCreateTool();
  const updateMutation = useUpdateTool();
  const toggleMutation = useToggleToolStatus();
  const deleteMutation = useDeleteTool();
  const { toast } = useToast();

  const rows = useMemo(() => (data?.items ?? []).map(toToolRow), [data]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ToolRow | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [deleting, setDeleting] = useState<ToolRow | null>(null);
  const [formError, setFormError] = useState("");

  const statCards = [
    { label: "Total Tools", value: String(data?.total ?? 0), icon: Wrench },
    {
      label: "Active Tools",
      value: String(dashboard?.active_tools ?? 0),
      icon: Wrench,
    },
    {
      label: "Disabled Tools",
      value: String((data?.total ?? 0) - (dashboard?.active_tools ?? 0)),
      icon: Wrench,
    },
  ];

  const openCreate = () => {
    setFormError("");
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (tool: ToolRow) => {
    setFormError("");
    setEditing(tool);
    setForm({
      name: tool.name,
      description: tool.description,
      type: (CATEGORIES.includes(tool.category as ToolType)
        ? tool.category
        : "utility") as ToolType,
      is_active: tool.status === "Active",
    });
    setModalOpen(true);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.name.trim() || !form.description.trim()) return;
    setFormError("");
    try {
      if (editing) {
        await updateMutation.mutateAsync({
          toolId: editing.id,
          payload: {
            name: form.name.trim(),
            description: form.description.trim(),
            type: form.type,
          },
        });
        toast("Tool updated successfully.", "success");
      } else {
        await createMutation.mutateAsync({
          name: form.name.trim(),
          description: form.description.trim(),
          type: form.type,
          is_active: form.is_active,
        });
        toast("Tool created successfully.", "success");
      }
      setModalOpen(false);
    } catch (err) {
      setFormError(
        err instanceof APIError ? err.message : "Unable to save the tool.",
      );
    }
  };

  const toggleStatus = async (tool: ToolRow) => {
    try {
      await toggleMutation.mutateAsync({
        toolId: tool.id,
        isActive: tool.status !== "Active",
      });
      toast(
        `Tool ${tool.status === "Active" ? "disabled" : "enabled"}.`,
        "success",
      );
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to update the tool.",
        "error",
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      toast("Tool deleted successfully.", "success");
      setDeleting(null);
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to delete the tool.",
        "error",
      );
    }
  };

  const columns: Column<ToolRow>[] = [
    { key: "name", header: "Tool", render: (row) => row.name },
    {
      key: "description",
      header: "Description",
      render: (row) => row.description,
    },
    { key: "category", header: "Category", render: (row) => row.category },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <button
          type="button"
          className={`pill toggle-pill ${row.status.toLowerCase()}`}
          onClick={() => toggleStatus(row)}
          aria-pressed={row.status === "Active"}
          title="Toggle status"
        >
          {row.status}
        </button>
      ),
    },
    { key: "updated", header: "Updated", render: (row) => row.updated },
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
            aria-label="Edit tool"
            title="Edit"
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="btn-action danger"
            onClick={() => setDeleting(row)}
            aria-label="Delete tool"
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
        title="Agent Tools"
        subtitle="Tools the agent can call during a conversation."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={openCreate}
          >
            <Plus size={15} />
            Add Tool
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
          <h2>Tool Registry</h2>
          <span className="card-badge">{rows.length} shown</span>
        </div>
        {isLoading ? (
          <LoadingState label="Loading tools…" />
        ) : error ? (
          <ErrorState
            error={error}
            context="Unable to load tools."
            onRetry={() => refetch()}
          />
        ) : (
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(row) => row.id}
            emptyMessage="No tools configured. Add one to get started."
          />
        )}
      </section>

      <Modal
        open={modalOpen}
        title={editing ? "Edit Tool" : "Add Tool"}
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
              form="tool-form"
              className="btn btn-primary"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Saving…"
                : "Save Tool"}
            </button>
          </>
        }
      >
        <form id="tool-form" className="modal-form" onSubmit={handleSubmit}>
          <label className="modal-field">
            <span>Tool Name</span>
            <input
              required
              value={form.name}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              placeholder="e.g. Web Search"
            />
          </label>
          <label className="modal-field">
            <span>Description</span>
            <input
              required
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              placeholder="What does this tool do?"
            />
          </label>
          <label className="modal-field">
            <span>Category</span>
            <select
              className="select"
              value={form.type}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  type: event.target.value as ToolType,
                }))
              }
            >
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          {formError && <p className="login-error">{formError}</p>}
        </form>
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete Tool"
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
            Are you sure you want to delete the tool{" "}
            <strong>{deleting.name}</strong>? This action cannot be undone.
          </p>
        )}
      </Modal>
    </div>
  );
}
