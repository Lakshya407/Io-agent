import {
  BookOpen,
  Database,
  FileText,
  HardDrive,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import StatCard from "../../components/admin/StatCard";
import StatusBadge from "../../components/admin/StatusBadge";
import {
  embeddingModelOptions,
  kbStats,
  knowledgeBases as initialKbs,
  type KnowledgeBaseRow,
} from "../../data/knowledgeBase";

const statCards = [
  { label: "Total Knowledge Bases", value: String(kbStats.total), icon: BookOpen },
  { label: "Documents", value: kbStats.documents, icon: FileText },
  { label: "Indexed Documents", value: kbStats.indexed, icon: Database },
  { label: "Storage Used", value: kbStats.storageUsed, icon: HardDrive },
];

const emptyForm = {
  name: "",
  description: "",
  embeddingModel: embeddingModelOptions[0],
  status: "Ready" as KnowledgeBaseRow["status"],
};

export default function AdminKnowledgeBase() {
  const [rows, setRows] = useState<KnowledgeBaseRow[]>(initialKbs);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<KnowledgeBaseRow | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [viewing, setViewing] = useState<KnowledgeBaseRow | null>(null);
  const [deleting, setDeleting] = useState<KnowledgeBaseRow | null>(null);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setFormOpen(true);
  };

  const openEdit = (kb: KnowledgeBaseRow) => {
    setEditing(kb);
    setForm({
      name: kb.name,
      description: kb.description,
      embeddingModel: kb.embeddingModel,
      status: kb.status,
    });
    setFormOpen(true);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!form.name.trim()) return;
    if (editing) {
      setRows((current) =>
        current.map((kb) =>
          kb.id === editing.id
            ? {
                ...kb,
                name: form.name.trim(),
                description: form.description.trim(),
                embeddingModel: form.embeddingModel,
                status: form.status,
                updated: "Just now",
              }
            : kb,
        ),
      );
    } else {
      setRows((current) => [
        ...current,
        {
          id: `kb${Date.now()}`,
          name: form.name.trim(),
          description: form.description.trim() || "No description provided.",
          documents: 0,
          indexed: 0,
          size: "0 GB",
          status: form.status,
          updated: "Just now",
          embeddingModel: form.embeddingModel,
        },
      ]);
    }
    setFormOpen(false);
  };

  const confirmDelete = () => {
    if (!deleting) return;
    setRows((current) => current.filter((kb) => kb.id !== deleting.id));
    setDeleting(null);
  };

  const columns: Column<KnowledgeBaseRow>[] = [
    { key: "name", header: "Knowledge Base", render: (row) => row.name },
    {
      key: "documents",
      header: "Documents",
      render: (row) => row.documents,
    },
    { key: "indexed", header: "Indexed", render: (row) => row.indexed },
    { key: "size", header: "Size", render: (row) => row.size },
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
        <div className="row-actions">
          <button
            type="button"
            className="btn-action"
            onClick={() => setViewing(row)}
            aria-label="View knowledge base"
            title="View"
          >
            <FileText size={15} />
          </button>
          <button
            type="button"
            className="btn-action"
            onClick={() => openEdit(row)}
            aria-label="Edit knowledge base"
            title="Edit"
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="btn-action danger"
            onClick={() => setDeleting(row)}
            aria-label="Delete knowledge base"
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
        title="Knowledge Base"
        subtitle="Document sources used for retrieval-augmented generation."
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={openCreate}
          >
            <Plus size={15} />
            Create Knowledge Base
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
          <h2>Knowledge Bases</h2>
          <span className="card-badge">{rows.length} shown</span>
        </div>
        <DataTable columns={columns} rows={rows} rowKey={(row) => row.id} />
      </section>

      <Modal
        open={formOpen}
        title={editing ? "Edit Knowledge Base" : "Create Knowledge Base"}
        onClose={() => setFormOpen(false)}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setFormOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="kb-form"
              className="btn btn-primary"
            >
              {editing ? "Save Changes" : "Create"}
            </button>
          </>
        }
      >
        <form id="kb-form" className="modal-form" onSubmit={handleSubmit}>
          <label className="modal-field">
            <span>Knowledge Base Name</span>
            <input
              required
              value={form.name}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              placeholder="e.g. Company Documentation"
            />
          </label>
          <label className="modal-field">
            <span>Description</span>
            <input
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              placeholder="Short description"
            />
          </label>
          <label className="modal-field">
            <span>Embedding Model</span>
            <select
              className="select"
              value={form.embeddingModel}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  embeddingModel: event.target.value,
                }))
              }
            >
              {embeddingModelOptions.map((model) => (
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
                  status: event.target.value as KnowledgeBaseRow["status"],
                }))
              }
            >
              <option value="Ready">Ready</option>
              <option value="Processing">Processing</option>
            </select>
          </label>
        </form>
      </Modal>

      <Modal
        open={viewing !== null}
        title="Knowledge Base Details"
        onClose={() => setViewing(null)}
        footer={
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setViewing(null)}
          >
            Close
          </button>
        }
      >
        {viewing && (
          <div className="detail-list">
            <div className="detail-row">
              <span>Name</span>
              <strong>{viewing.name}</strong>
            </div>
            <div className="detail-row">
              <span>Description</span>
              <strong>{viewing.description}</strong>
            </div>
            <div className="detail-row">
              <span>Documents</span>
              <strong>{viewing.documents}</strong>
            </div>
            <div className="detail-row">
              <span>Indexed</span>
              <strong>{viewing.indexed}</strong>
            </div>
            <div className="detail-row">
              <span>Size</span>
              <strong>{viewing.size}</strong>
            </div>
            <div className="detail-row">
              <span>Embedding Model</span>
              <strong>{viewing.embeddingModel}</strong>
            </div>
            <div className="detail-row">
              <span>Status</span>
              <strong>{viewing.status}</strong>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete Knowledge Base"
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
            >
              <Trash2 size={15} />
              Delete
            </button>
          </>
        }
      >
        {deleting && (
          <p className="modal-warning">
            Are you sure you want to delete <strong>{deleting.name}</strong>?
            This is a demo action and no documents are actually removed.
          </p>
        )}
      </Modal>
    </div>
  );
}
