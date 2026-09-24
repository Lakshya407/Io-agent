import { FileText, Pencil, Plus, Star, Trash2 } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import StatusBadge from "../../components/admin/StatusBadge";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import {
  useCreatePrompt,
  useDeletePrompt,
  usePrompts,
  useUpdatePrompt,
} from "../../hooks/usePrompts";
import { useModels } from "../../hooks/useModels";
import { APIError } from "../../types/common";
import type { Prompt, PromptStatus } from "../../types/prompt";
import { formatRelativeTime } from "../../utils/format";

const STATUSES: PromptStatus[] = ["active", "draft", "inactive"];

const emptyForm = {
  name: "",
  purpose: "",
  model: "",
  version: 1,
  status: "draft" as PromptStatus,
  content: "",
  is_default: false,
};

export default function AdminPrompts() {
  const { data, isLoading, error, refetch } = usePrompts();
  const { data: modelCatalog } = useModels({ activeOnly: true });
  const createMutation = useCreatePrompt();
  const updateMutation = useUpdatePrompt();
  const deleteMutation = useDeletePrompt();
  const { toast } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Prompt | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [deleting, setDeleting] = useState<Prompt | null>(null);
  const [confirmingDefault, setConfirmingDefault] = useState<Prompt | null>(null);
  const [formError, setFormError] = useState("");

  const rows = useMemo(() => data?.items ?? [], [data]);
  const activeCount = rows.filter((row) => row.status === "active").length;
  const defaultPrompt = rows.find((row) => row.is_default);

  const statCards = [
    { label: "System Prompts", value: String(data?.total ?? 0), icon: FileText },
    { label: "Active Prompts", value: String(activeCount), icon: FileText },
    { label: "Default Prompt", value: defaultPrompt?.name ?? "—", icon: Star },
  ];

  const openCreate = () => {
    setFormError("");
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (prompt: Prompt) => {
    setFormError("");
    setEditing(prompt);
    setForm({
      name: prompt.name,
      purpose: prompt.purpose,
      model: prompt.model ?? "",
      version: prompt.version,
      status: prompt.status,
      content: prompt.content,
      is_default: prompt.is_default,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.name.trim() || !form.content.trim()) return;
    setFormError("");
    const payload = {
      name: form.name.trim(),
      purpose: form.purpose.trim(),
      model: form.model || null,
      version: Number.isFinite(form.version) ? form.version : 1,
      status: form.status,
      content: form.content,
      is_default: form.is_default,
    };
    try {
      if (editing) {
        await updateMutation.mutateAsync({ promptId: editing.id, payload });
        toast("Prompt updated successfully.", "success");
      } else {
        await createMutation.mutateAsync(payload);
        toast("Prompt created successfully.", "success");
      }
      setModalOpen(false);
    } catch (err) {
      setFormError(
        err instanceof APIError ? err.message : "Unable to save the prompt.",
      );
    }
  };

  const setDefault = async (prompt: Prompt) => {
    try {
      await updateMutation.mutateAsync({
        promptId: prompt.id,
        payload: { is_default: true },
      });
      toast(`Default prompt set to ${prompt.name}.`, "success");
      setConfirmingDefault(null);
    } catch (err) {
      setConfirmingDefault(null);
      toast(
        err instanceof APIError ? err.message : "Unable to set the default.",
        "error",
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      toast("Prompt deleted successfully.", "success");
      setDeleting(null);
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to delete the prompt.",
        "error",
      );
    }
  };

  // Keep the model select showing the stored value even if the model is no
  // longer in the active catalog.
  const modelOptions = useMemo(() => {
    const names = (modelCatalog?.items ?? []).map((item) => item.name);
    if (form.model && !names.includes(form.model)) names.unshift(form.model);
    return names;
  }, [modelCatalog, form.model]);

  const columns: Column<Prompt>[] = [
    { key: "name", header: "Prompt", render: (row) => row.name },
    { key: "purpose", header: "Purpose", render: (row) => row.purpose || "—" },
    { key: "model", header: "Model", render: (row) => row.model ?? "Any" },
    {
      key: "version",
      header: "Version",
      render: (row) => `v${row.version}`,
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "default",
      header: "Default",
      render: (row) =>
        row.is_default ? (
          <span className="pill default">Default</span>
        ) : (
          <button
            type="button"
            className="btn-action"
            onClick={() => setConfirmingDefault(row)}
            aria-label={`Set ${row.name} as default`}
            title="Set as default"
          >
            <Star size={15} />
          </button>
        ),
    },
    {
      key: "updated",
      header: "Updated",
      render: (row) => formatRelativeTime(row.updated_at),
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
            aria-label="Edit prompt"
            title="Edit"
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="btn-action danger"
            onClick={() => setDeleting(row)}
            aria-label="Delete prompt"
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
        title="Prompt Management"
        subtitle="System prompts that shape agent behavior."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={openCreate}
          >
            <Plus size={15} />
            Create Prompt
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
          <h2>System Prompts</h2>
          <span className="card-badge">{data?.total ?? 0} prompts</span>
        </div>
        {isLoading ? (
          <LoadingState label="Loading prompts…" />
        ) : error ? (
          <ErrorState
            error={error}
            context="Unable to load prompts."
            onRetry={() => refetch()}
          />
        ) : (
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(row) => row.id}
            emptyMessage="No prompts configured. Create one to get started."
          />
        )}
      </section>

      <Modal
        open={modalOpen}
        title={editing ? "Edit Prompt" : "Create Prompt"}
        size="lg"
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
              form="prompt-form"
              className="btn btn-primary"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Saving…"
                : "Save Prompt"}
            </button>
          </>
        }
      >
        <form id="prompt-form" className="modal-form" onSubmit={handleSubmit}>
          <label className="modal-field">
            <span>Prompt Name</span>
            <input
              required
              value={form.name}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              placeholder="e.g. Default Assistant"
            />
          </label>
          <label className="modal-field">
            <span>Purpose</span>
            <input
              value={form.purpose}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  purpose: event.target.value,
                }))
              }
              placeholder="e.g. General agent behavior"
            />
          </label>
          <label className="modal-field">
            <span>System Prompt</span>
            <textarea
              rows={7}
              required
              value={form.content}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  content: event.target.value,
                }))
              }
              placeholder="Enter the system prompt…"
            />
          </label>
          <div className="modal-field-row">
            <label className="modal-field">
              <span>Model</span>
              <select
                className="select"
                value={form.model}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    model: event.target.value,
                  }))
                }
              >
                <option value="">Any model</option>
                {modelOptions.map((model) => (
                  <option key={model} value={model}>
                    {model}
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
                    status: event.target.value as PromptStatus,
                  }))
                }
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="modal-field-row">
            <label className="modal-field">
              <span>Version</span>
              <input
                type="number"
                min={1}
                value={form.version}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    version: Number(event.target.value),
                  }))
                }
              />
            </label>
            <label className="remember">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    is_default: event.target.checked,
                  }))
                }
              />
              Default prompt
            </label>
          </div>
          {formError && <p className="login-error">{formError}</p>}
        </form>
      </Modal>

      <Modal
        open={confirmingDefault !== null}
        title="Set Default Prompt"
        size="sm"
        onClose={() => setConfirmingDefault(null)}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setConfirmingDefault(null)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => confirmingDefault && setDefault(confirmingDefault)}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? "Setting…" : "Set as Default"}
            </button>
          </>
        }
      >
        {confirmingDefault && (
          <p className="modal-warning">
            Make <strong>{confirmingDefault.name}</strong> the default prompt?
            The previous default is cleared automatically.
          </p>
        )}
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete Prompt"
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
            Are you sure you want to delete the prompt{" "}
            <strong>{deleting.name}</strong>? This action cannot be undone.
          </p>
        )}
      </Modal>
    </div>
  );
}
