import { Cpu, Pencil, Plus, Trash2 } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import { useAdminDashboard } from "../../hooks/useAdmin";
import {
  useCreateModel,
  useDeleteModel,
  useModels,
  useToggleModelStatus,
  useUpdateModel,
} from "../../hooks/useModels";
import { toModelRow, type ModelRow } from "../../utils/adapters";
import { formatRelativeTime } from "../../utils/format";
import { APIError } from "../../types/common";
import type { ModelProvider, ModelType } from "../../types/model";

const PROVIDERS: ModelProvider[] = ["openai", "anthropic", "ollama", "custom"];
const TYPES: ModelType[] = ["chat", "code", "embedding"];

const emptyForm = {
  name: "",
  provider: "custom" as ModelProvider,
  model_identifier: "",
  model_type: "chat" as ModelType,
  max_tokens: 128000,
  temperature: 0.7,
  is_active: true,
};

export default function AdminModels() {
  const { data, isLoading, error, refetch } = useModels({ activeOnly: false });
  const { data: dashboard } = useAdminDashboard();
  const createMutation = useCreateModel();
  const updateMutation = useUpdateModel();
  const toggleMutation = useToggleModelStatus();
  const deleteMutation = useDeleteModel();
  const { toast } = useToast();

  const rows = useMemo(
    () => (data?.items ?? []).map(toModelRow),
    [data],
  );

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ModelRow | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [deleting, setDeleting] = useState<ModelRow | null>(null);
  const [formError, setFormError] = useState("");

  const statCards = [
    {
      label: "Total Models",
      value: String(data?.total ?? 0),
      icon: Cpu,
    },
    {
      label: "Active Models",
      value: String(dashboard?.active_models ?? 0),
      icon: Cpu,
    },
    {
      label: "Inactive Models",
      value: String(
        (data?.total ?? 0) - (dashboard?.active_models ?? 0),
      ),
      icon: Cpu,
    },
    {
      label: "Default Model",
      value: rows.find((row) => row.isDefault)?.name ?? "—",
      icon: Cpu,
    },
  ];

  const openCreate = () => {
    setFormError("");
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (model: ModelRow) => {
    setFormError("");
    setEditing(model);
    setForm({
      name: model.name,
      provider: (PROVIDERS.includes(
        model.provider as ModelProvider,
      )
        ? model.provider
        : "custom") as ModelProvider,
      model_identifier: model.modelIdentifier,
      model_type: (TYPES.includes(model.type as ModelType)
        ? model.type
        : "chat") as ModelType,
      max_tokens: model.maxTokens,
      temperature: model.temperature,
      is_active: model.status === "Active",
    });
    setModalOpen(true);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.name.trim() || !form.model_identifier.trim()) return;
    setFormError("");
    try {
      if (editing) {
        await updateMutation.mutateAsync({
          modelId: editing.id,
          payload: {
            name: form.name.trim(),
            provider: form.provider,
            model_identifier: form.model_identifier.trim(),
            model_type: form.model_type,
            max_tokens: form.max_tokens,
            temperature: form.temperature,
          },
        });
        toast("Model updated successfully.", "success");
      } else {
        await createMutation.mutateAsync({
          name: form.name.trim(),
          provider: form.provider,
          model_identifier: form.model_identifier.trim(),
          model_type: form.model_type,
          is_active: form.is_active,
          max_tokens: form.max_tokens,
          temperature: form.temperature,
        });
        toast("Model created successfully.", "success");
      }
      setModalOpen(false);
    } catch (err) {
      setFormError(
        err instanceof APIError ? err.message : "Unable to save the model.",
      );
    }
  };

  const toggleStatus = async (model: ModelRow) => {
    try {
      await toggleMutation.mutateAsync({
        modelId: model.id,
        isActive: model.status !== "Active",
      });
      toast(
        `Model ${model.status === "Active" ? "disabled" : "enabled"}.`,
        "success",
      );
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to update the model.",
        "error",
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      toast("Model deleted successfully.", "success");
      setDeleting(null);
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to delete the model.",
        "error",
      );
    }
  };

  const columns: Column<ModelRow>[] = [
    { key: "name", header: "Model", render: (row) => row.name },
    { key: "provider", header: "Provider", render: (row) => row.provider },
    { key: "modelIdentifier", header: "Identifier", render: (row) => row.modelIdentifier },
    { key: "type", header: "Type", render: (row) => row.type },
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
    {
      key: "maxTokens",
      header: "Max Tokens",
      render: (row) => row.maxTokens.toLocaleString(),
    },
    { key: "created", header: "Created", render: (row) => row.created },
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
            aria-label="Edit model"
            title="Edit"
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="btn-action danger"
            onClick={() => setDeleting(row)}
            aria-label="Delete model"
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
        title="Models"
        subtitle="Available LLM configurations and their usage."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={openCreate}
          >
            <Plus size={15} />
            Add Model
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
          <h2>Configured Models</h2>
          <span className="card-badge">{rows.length} shown</span>
        </div>
        {isLoading ? (
          <LoadingState label="Loading models…" />
        ) : error ? (
          <ErrorState
            error={error}
            context="Unable to load models."
            onRetry={() => refetch()}
          />
        ) : (
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(row) => row.id}
            emptyMessage="No models configured. Add one to get started."
          />
        )}
      </section>

      <Modal
        open={modalOpen}
        title={editing ? "Edit Model" : "Add Model"}
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
              form="model-form"
              className="btn btn-primary"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Saving…"
                : "Save Model"}
            </button>
          </>
        }
      >
        <form id="model-form" className="modal-form" onSubmit={handleSubmit}>
          <label className="modal-field">
            <span>Model Name</span>
            <input
              required
              value={form.name}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              placeholder="e.g. GPT-OSS 20B"
            />
          </label>
          <label className="modal-field">
            <span>Model Identifier</span>
            <input
              required
              value={form.model_identifier}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  model_identifier: event.target.value,
                }))
              }
              placeholder="e.g. gpt-oss-20b"
            />
          </label>
          <div className="modal-field-row">
            <label className="modal-field">
              <span>Provider</span>
              <select
                className="select"
                value={form.provider}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    provider: event.target.value as ModelProvider,
                  }))
                }
              >
                {PROVIDERS.map((provider) => (
                  <option key={provider} value={provider}>
                    {provider}
                  </option>
                ))}
              </select>
            </label>
            <label className="modal-field">
              <span>Model Type</span>
              <select
                className="select"
                value={form.model_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    model_type: event.target.value as ModelType,
                  }))
                }
              >
                {TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="modal-field-row">
            <label className="modal-field">
              <span>Max Tokens</span>
              <input
                type="number"
                min={1}
                value={form.max_tokens}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    max_tokens: Number(event.target.value),
                  }))
                }
              />
            </label>
            <label className="modal-field">
              <span>Temperature</span>
              <input
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={form.temperature}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    temperature: Number(event.target.value),
                  }))
                }
              />
            </label>
          </div>
          {formError && <p className="login-error">{formError}</p>}
        </form>
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete Model"
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
            Are you sure you want to delete the model{" "}
            <strong>{deleting.name}</strong>? This action cannot be undone.
          </p>
        )}
      </Modal>
    </div>
  );
}
