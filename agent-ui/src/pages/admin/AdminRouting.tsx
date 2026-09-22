import { ChevronDown, ChevronUp, Plus, Workflow } from "lucide-react";
import { useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import {
  modelOptions,
  requestTypeOptions,
  routingRules as initialRules,
  type RoutingRule,
} from "../../data/models";

const emptyForm = {
  requestType: requestTypeOptions[0],
  primaryModel: modelOptions[0],
  fallbackModel: modelOptions[3],
  status: "Active" as RoutingRule["status"],
};

export default function AdminRouting() {
  const [rules, setRules] = useState<RoutingRule[]>(initialRules);
  const [modalOpen, setModalOpen] = useState(false);
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

  const updateModel = (
    id: string,
    field: "primaryModel" | "fallbackModel",
    value: string,
  ) => {
    setRules((current) =>
      current.map((rule) =>
        rule.id === id ? { ...rule, [field]: value } : rule,
      ),
    );
  };

  const movePriority = (id: string, direction: "up" | "down") => {
    setRules((current) => {
      const index = current.findIndex((rule) => rule.id === id);
      const target = direction === "up" ? index - 1 : index + 1;
      if (index === -1 || target < 0 || target >= current.length) {
        return current;
      }
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next.map((rule, priority) => ({ ...rule, priority: priority + 1 }));
    });
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setRules((current) => [
      ...current,
      {
        id: `r${Date.now()}`,
        priority: current.length + 1,
        requestType: form.requestType,
        primaryModel: form.primaryModel,
        fallbackModel: form.fallbackModel,
        status: form.status,
      },
    ]);
    setForm(emptyForm);
    setModalOpen(false);
  };

  const columns: Column<RoutingRule>[] = [
    {
      key: "priority",
      header: "Priority",
      render: (row) => (
        <div className="priority-cell">
          <span className="priority-value">{row.priority}</span>
          <span className="priority-buttons">
            <button
              type="button"
              className="btn-action"
              onClick={() => movePriority(row.id, "up")}
              disabled={row.priority === 1}
              aria-label="Move up"
              title="Increase priority"
            >
              <ChevronUp size={14} />
            </button>
            <button
              type="button"
              className="btn-action"
              onClick={() => movePriority(row.id, "down")}
              disabled={row.priority === rules.length}
              aria-label="Move down"
              title="Decrease priority"
            >
              <ChevronDown size={14} />
            </button>
          </span>
        </div>
      ),
    },
    {
      key: "requestType",
      header: "Request Type",
      render: (row) => row.requestType,
    },
    {
      key: "primaryModel",
      header: "Primary Model",
      render: (row) => (
        <select
          className="select"
          value={row.primaryModel}
          onChange={(event) =>
            updateModel(row.id, "primaryModel", event.target.value)
          }
          aria-label="Primary model"
        >
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
          value={row.fallbackModel}
          onChange={(event) =>
            updateModel(row.id, "fallbackModel", event.target.value)
          }
          aria-label="Fallback model"
        >
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
          className={`pill toggle-pill ${row.status.toLowerCase()}`}
          onClick={() => toggleStatus(row.id)}
          aria-pressed={row.status === "Active"}
          title="Toggle rule"
        >
          {row.status}
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
            onClick={() => setModalOpen(true)}
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
        <DataTable
          columns={columns}
          rows={rules}
          rowKey={(row) => row.id}
          emptyMessage="No routing rules configured."
        />
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
            >
              Save Rule
            </button>
          </>
        }
      >
        <form id="add-rule-form" className="modal-form" onSubmit={handleSubmit}>
          <label className="modal-field">
            <span>Request Type</span>
            <select
              className="select"
              value={form.requestType}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  requestType: event.target.value,
                }))
              }
            >
              {requestTypeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="modal-field">
            <span>Primary Model</span>
            <select
              className="select"
              value={form.primaryModel}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  primaryModel: event.target.value,
                }))
              }
            >
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
                  status: event.target.value as RoutingRule["status"],
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
