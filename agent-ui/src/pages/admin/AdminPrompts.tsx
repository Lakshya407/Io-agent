import { FileText, Pencil, Plus, Send, Save } from "lucide-react";
import { useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import StatusBadge from "../../components/admin/StatusBadge";
import {
  defaultSystemPrompt,
  promptStats,
  prompts as initialPrompts,
  type PromptRow,
} from "../../data/prompts";

const statCards = [
  {
    label: "System Prompts",
    value: String(promptStats.systemPrompts),
    icon: FileText,
  },
  {
    label: "Active Prompts",
    value: String(promptStats.activePrompts),
    icon: FileText,
  },
];

const modelOptions = [
  "GPT-OSS 20B",
  "Qwen 2.5 72B",
  "Llama 3.3 70B",
  "Mistral Small",
];

const emptyForm = {
  name: "",
  purpose: "",
  model: modelOptions[0],
  version: "v1",
  status: "Draft" as PromptRow["status"],
  systemPrompt: defaultSystemPrompt,
};

export default function AdminPrompts() {
  const [rows, setRows] = useState<PromptRow[]>(initialPrompts);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<PromptRow | null>(null);
  const [form, setForm] = useState(emptyForm);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (prompt: PromptRow) => {
    setEditing(prompt);
    setForm({
      name: prompt.name,
      purpose: prompt.purpose,
      model: prompt.model,
      version: prompt.version,
      status: prompt.status,
      systemPrompt: prompt.systemPrompt,
    });
    setModalOpen(true);
  };

  const persist = (status: PromptRow["status"]) => {
    if (!form.name.trim()) return;
    if (editing) {
      setRows((current) =>
        current.map((prompt) =>
          prompt.id === editing.id
            ? {
                ...prompt,
                name: form.name.trim(),
                purpose: form.purpose.trim(),
                model: form.model,
                version: form.version,
                status,
                systemPrompt: form.systemPrompt,
                updated: "Just now",
              }
            : prompt,
        ),
      );
    } else {
      setRows((current) => [
        ...current,
        {
          id: `p${Date.now()}`,
          name: form.name.trim(),
          purpose: form.purpose.trim() || "General purpose",
          model: form.model,
          version: form.version,
          status,
          updated: "Just now",
          systemPrompt: form.systemPrompt,
        },
      ]);
    }
    setModalOpen(false);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    persist("Draft");
  };

  const columns: Column<PromptRow>[] = [
    { key: "name", header: "Prompt", render: (row) => row.name },
    { key: "purpose", header: "Purpose", render: (row) => row.purpose },
    { key: "model", header: "Model", render: (row) => row.model },
    { key: "version", header: "Version", render: (row) => row.version },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    { key: "updated", header: "Updated", render: (row) => row.updated },
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
          <span className="card-badge">{rows.length} shown</span>
        </div>
        <DataTable columns={columns} rows={rows} rowKey={(row) => row.id} />
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
              className="btn btn-secondary"
            >
              <Save size={15} />
              Save Draft
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => persist("Active")}
            >
              <Send size={15} />
              Publish
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => persist("Active")}
            >
              Activate
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
              rows={6}
              value={form.systemPrompt}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  systemPrompt: event.target.value,
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
                {modelOptions.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </label>
            <label className="modal-field">
              <span>Version</span>
              <input
                value={form.version}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    version: event.target.value,
                  }))
                }
                placeholder="v1"
              />
            </label>
          </div>
        </form>
      </Modal>
    </div>
  );
}
