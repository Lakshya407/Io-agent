import { ChevronDown, ChevronUp, Plus, Trash2, Workflow } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import { useModels } from "../../hooks/useModels";
import {
  useCreateRoutingRule,
  useDeleteRoutingRule,
  useReorderRoutingRules,
  useRoutingRules,
  useUpdateRoutingRule,
} from "../../hooks/useRouting";
import { APIError } from "../../types/common";
import type { RoutingRule } from "../../types/routing";

const emptyForm = {
  requestType: "",
  primaryModel: "",
  fallbackModel: "",
  isActive: true,
};

export default function AdminRouting() {
  const { data: rules, isLoading, error, refetch } = useRoutingRules();
  const { data: modelCatalog } = useModels({ activeOnly: true });
  const createMutation = useCreateRoutingRule();
  const updateMutation = useUpdateRoutingRule();
  const reorderMutation = useReorderRoutingRules();
  const deleteMutation = useDeleteRoutingRule();
  const { toast } = useToast();

  const [modalOpen, setModalOpen] = useState(false);
  const [deleting, setDeleting] = useState<RoutingRule | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState("");

  const list = rules ?? [];

  // Active catalog names, unioned with whatever a rule already references so
  // an in-place select never blanks out a model that went inactive.
  const modelOptions = useMemo(() => {
    const names = new Set<string>((modelCatalog?.items ?? []).map((m) => m.name));
    for (const rule of list) {
      names.add(rule.primary_model);
      if (rule.fallback_model) names.add(rule.fallback_model);
    }
    if (form.primaryModel) names.add(form.primaryModel);
    if (form.fallbackModel) names.add(form.fallbackModel);
    return [...names];
  }, [modelCatalog, list, form.primaryModel, form.fallbackModel]);

  const guardPending = () =>
    updateMutation.isPending || reorderMutation.isPending;

  const patchRule = async (
    ruleId: string,
    payload: Parameters<typeof updateMutation.mutateAsync>[0]["payload"],
  ) => {
    try {
      await updateMutation.mutateAsync({ ruleId, payload });
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to update the rule.",
        "error",
      );
      // Pull the table back to the server truth after a rejected edit.
      void refetch();
    }
  };

  const movePriority = async (index: number, direction: "up" | "down") => {
    const target = direction === "up" ? index - 1 : index + 1;
    if (index === -1 || target < 0 || target >= list.length) return;
    const ids = list.map((rule) => rule.id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    try {
      await reorderMutation.mutateAsync(ids);
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to reorder the rules.",
        "error",
      );
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.requestType.trim() || !form.primaryModel) return;
    setFormError("");
    try {
      await createMutation.mutateAsync({
        request_type: form.requestType.trim(),
        primary_model: form.primaryModel,
        fallback_model: form.fallbackModel || null,
        is_active: form.isActive,
      });
      toast("Routing rule created.", "success");
      setForm(emptyForm);
      setModalOpen(false);
    } catch (err) {
      setFormError(
        err instanceof APIError ? err.message : "Unable to create the rule.",
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      toast("Routing rule deleted.", "success");
      setDeleting(null);
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to delete the rule.",
        "error",
      );
    }
  };

  const columns: Column<RoutingRule>[] = [
    {
      key: "priority",
      header: "Priority",
      render: (row) => {
        const index = list.findIndex((rule) => rule.id === row.id);
        return (
          <div className="priority-cell">
            <span className="priority-value">{row.priority}</span>
            <span className="priority-buttons">
              <button
                type="button"
                className="btn-action"
                onClick={() => void movePriority(index, "up")}
                disabled={index <= 0 || guardPending()}
                aria-label="Move up"
                title="Increase priority"
              >
                <ChevronUp size={14} />
              </button>
              <button
                type="button"
                className="btn-action"
                onClick={() => void movePriority(index, "down")}
                disabled={index >= list.length - 1 || guardPending()}
                aria-label="Move down"
                title="Decrease priority"
              >
                <ChevronDown size={14} />
              </button>
            </span>
          </div>
        );
      },
    },
    {
      key: "requestType",
      header: "Request Type",
      render: (row) => row.request_type,
    },
    {
      key: "primaryModel",
      header: "Primary Model",
      render: (row) => (
        <select
          className="select"
          value={row.primary_model}
          disabled={guardPending()}
          onChange={(event) =>
            void patchRule(row.id, { primary_model: event.target.value })
          }
          aria-label={`Primary model for ${row.request_type}`}
        >
          {!modelOptions.includes(row.primary_model) && (
            <option value={row.primary_model}>{row.primary_model}</option>
          )}
          {modelOptions.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      ),
    },
    {
      key: "fallbackModel",
      header: "Fallback Model",
      render: (row) => (
        <select
          className="select"
          value={row.fallback_model ?? ""}
          disabled={guardPending()}
          onChange={(event) =>
            void patchRule(row.id, {
              fallback_model: event.target.value || null,
            })
          }
          aria-label={`Fallback model for ${row.request_type}`}
        >
          <option value="">None</option>
          {!modelOptions.includes(row.fallback_model ?? "") &&
            row.fallback_model && (
              <option value={row.fallback_model}>{row.fallback_model}</option>
            )}
          {modelOptions.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <button
          type="button"
          className={`pill toggle-pill ${row.is_active ? "active" : "inactive"}`}
          disabled={guardPending()}
          onClick={() =>
            void patchRule(row.id, { is_active: !row.is_active })
          }
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
        <button
          type="button"
          className="btn-action danger"
          onClick={() => setDeleting(row)}
          aria-label="Delete routing rule"
          title="Delete"
        >
          <Trash2 size={15} />
        </button>
      ),
    },
  ];

  return (
    <div className="admin-content">
      <PageHeader
        title="Model Routing"
        subtitle="Define which model should handle different types of requests."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setFormError("");
              setForm(emptyForm);
              setModalOpen(true);
            }}
          >
            <Plus size={15} />
            Add Routing Rule
          </button>
        }
      />

      <section className="admin-card">
        <div className="card-head">
          <h2>Routing Rules</h2>
          <Workflow size={16} className="card-icon" />
        </div>
        {isLoading ? (
          <LoadingState label="Loading routing rules…" />
        ) : error ? (
          <ErrorState
            error={error}
            context="Unable to load routing rules."
            onRetry={() => refetch()}
          />
        ) : (
          <DataTable
            columns={columns}
            rows={list}
            rowKey={(row) => row.id}
            emptyMessage="No routing rules configured. Requests fall back to the default model."
          />
        )}
      </section>

      <Modal
        open={modalOpen}
        title="Add Routing Rule"
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
              form="add-rule-form"
              className="btn btn-primary"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? "Saving…" : "Save Rule"}
            </button>
          </>
        }
      >
        <form id="add-rule-form" className="modal-form" onSubmit={handleSubmit}>
          <label className="modal-field">
            <span>Request Type</span>
            <input
              required
              value={form.requestType}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  requestType: event.target.value,
                }))
              }
              placeholder="e.g. Code"
            />
          </label>
          <label className="modal-field">
            <span>Primary Model</span>
            <select
              className="select"
              required
              value={form.primaryModel}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  primaryModel: event.target.value,
                }))
              }
            >
              <option value="">Select a model…</option>
              {modelOptions.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <label className="modal-field">
            <span>Fallback Model</span>
            <select
              className="select"
              value={form.fallbackModel}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  fallbackModel: event.target.value,
                }))
              }
            >
              <option value="">None</option>
              {modelOptions.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
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
          {formError && <p className="login-error">{formError}</p>}
        </form>
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete Routing Rule"
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
            Delete the rule for <strong>{deleting.request_type}</strong>? The
            remaining rules are renumbered automatically.
          </p>
        )}
      </Modal>
    </div>
  );
}
