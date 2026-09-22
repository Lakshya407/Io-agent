import { Eye, Pencil, Trash2, UserSearch } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { DataTable, type Column } from "../../components/admin/DataTable";
import FilterBar from "../../components/admin/FilterBar";
import Modal from "../../components/admin/Modal";
import PageHeader from "../../components/admin/PageHeader";
import Pagination from "../../components/admin/Pagination";
import StatCard from "../../components/admin/StatCard";
import StatusBadge from "../../components/admin/StatusBadge";
import { ErrorState, LoadingState } from "../../components/admin/QueryState";
import { useToast } from "../../context/ToastContext";
import { useAdminDashboard } from "../../hooks/useAdmin";
import {
  useDeleteUser,
  useUpdateUser,
  useUsers,
} from "../../hooks/useUsers";
import { toUserRow, type UserRow } from "../../utils/adapters";
import { APIError } from "../../types/common";
import type { UserAdminUpdate } from "../../types/user";

const PAGE_SIZE = 20;

export default function AdminUsers() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [selected, setSelected] = useState<UserRow | null>(null);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [deleting, setDeleting] = useState<UserRow | null>(null);
  const [formError, setFormError] = useState("");

  const { data, isLoading, error, refetch, isFetching } = useUsers({
    page,
    page_size: PAGE_SIZE,
  });
  const { data: dashboard } = useAdminDashboard();
  const updateMutation = useUpdateUser();
  const deleteMutation = useDeleteUser();
  const { toast } = useToast();

  const rows = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (data?.items ?? [])
      .map(toUserRow)
      .filter((user) => {
        const matchesQuery =
          !query ||
          user.name.toLowerCase().includes(query) ||
          user.email.toLowerCase().includes(query);
        const matchesStatus = !statusFilter || user.status === statusFilter;
        const matchesRole = !roleFilter || user.role === roleFilter;
        return matchesQuery && matchesStatus && matchesRole;
      });
  }, [data, search, statusFilter, roleFilter]);

  const statCards = dashboard
    ? [
        {
          label: "Total Users",
          value: String(dashboard.total_users),
          icon: UserSearch,
        },
        {
          label: "Active",
          value: String(dashboard.active_users),
          icon: UserSearch,
        },
        {
          label: "Inactive",
          value: String(dashboard.total_users - dashboard.active_users),
          icon: UserSearch,
        },
      ]
    : [];

  const openEdit = (user: UserRow) => {
    setFormError("");
    setEditing(user);
  };

  const submitEdit = async (event: FormEvent) => {
    event.preventDefault();
    if (!editing) return;
    const form = event.currentTarget as HTMLFormElement;
    const formData = new FormData(form);
    const payload: UserAdminUpdate = {
      name: String(formData.get("name") ?? "").trim() || null,
      email: String(formData.get("email") ?? "").trim() || null,
      role: formData.get("role") as "admin" | "user",
      is_active: formData.get("is_active") === "on",
    };
    setFormError("");
    try {
      await updateMutation.mutateAsync({ userId: editing.id, payload });
      toast("User updated successfully.", "success");
      setEditing(null);
      setSelected(null);
    } catch (err) {
      setFormError(
        err instanceof APIError ? err.message : "Unable to update the user.",
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      toast("User deleted successfully.", "success");
      setDeleting(null);
      setSelected(null);
    } catch (err) {
      toast(
        err instanceof APIError ? err.message : "Unable to delete the user.",
        "error",
      );
    }
  };

  const columns: Column<UserRow>[] = [
    { key: "name", header: "Name", render: (row) => row.name },
    { key: "email", header: "Email", render: (row) => row.email },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    { key: "role", header: "Role", render: (row) => row.role },
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
            onClick={() => setSelected(row)}
            aria-label="View user"
            title="View"
          >
            <Eye size={15} />
          </button>
          <button
            type="button"
            className="btn-action"
            onClick={() => openEdit(row)}
            aria-label="Edit user"
            title="Edit"
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="btn-action danger"
            onClick={() => setDeleting(row)}
            aria-label="Delete user"
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
      <PageHeader title="Users" subtitle="Manage user accounts and roles." />

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
          <h2>All Users</h2>
          <span className="card-badge">
            {data ? `${rows.length} shown · ${data.total} total` : "Loading…"}
          </span>
        </div>
        <FilterBar
          searchValue={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search users…"
          filters={[
            {
              label: "Status",
              value: statusFilter,
              options: ["Active", "Inactive"],
              onChange: setStatusFilter,
            },
            {
              label: "Role",
              value: roleFilter,
              options: ["Admin", "User"],
              onChange: setRoleFilter,
            },
          ]}
        />
        {isLoading ? (
          <LoadingState label="Loading users…" />
        ) : error ? (
          <ErrorState
            error={error}
            context="Unable to load users."
            onRetry={() => refetch()}
          />
        ) : (
          <>
            <DataTable
              columns={columns}
              rows={rows}
              rowKey={(row) => row.id}
              emptyMessage="No users match the selected filters."
            />
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={data?.total ?? 0}
              onPageChange={setPage}
              loading={isFetching}
            />
          </>
        )}
      </section>

      <Modal
        open={selected !== null}
        title="User Details"
        onClose={() => setSelected(null)}
        footer={
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setSelected(null)}
          >
            Close
          </button>
        }
      >
        {selected && (
          <div className="detail-list">
            <div className="detail-row">
              <span>Name</span>
              <strong>{selected.name}</strong>
            </div>
            <div className="detail-row">
              <span>Email</span>
              <strong>{selected.email}</strong>
            </div>
            <div className="detail-row">
              <span>Status</span>
              <strong>{selected.status}</strong>
            </div>
            <div className="detail-row">
              <span>Role</span>
              <strong>{selected.role}</strong>
            </div>
            <div className="detail-row">
              <span>Created</span>
              <strong>{selected.created}</strong>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={editing !== null}
        title="Edit User"
        onClose={() => setEditing(null)}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setEditing(null)}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="edit-user-form"
              className="btn btn-primary"
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? "Saving…" : "Save Changes"}
            </button>
          </>
        }
      >
        {editing && (
          <form
            id="edit-user-form"
            className="modal-form"
            onSubmit={submitEdit}
          >
            <label className="modal-field">
              <span>Name</span>
              <input name="name" defaultValue={editing.name} required />
            </label>
            <label className="modal-field">
              <span>Email</span>
              <input
                name="email"
                type="email"
                defaultValue={editing.email}
                required
              />
            </label>
            <label className="modal-field">
              <span>Role</span>
              <select
                name="role"
                defaultValue={editing.role === "Admin" ? "admin" : "user"}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </label>
            <label className="modal-field">
              <span>Status</span>
              <select
                name="is_active"
                defaultValue={editing.status === "Active" ? "on" : "off"}
              >
                <option value="on">Active</option>
                <option value="off">Inactive</option>
              </select>
            </label>
            {formError && <p className="login-error">{formError}</p>}
          </form>
        )}
      </Modal>

      <Modal
        open={deleting !== null}
        title="Delete User"
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
            Are you sure you want to delete <strong>{deleting.name}</strong>{" "}
            ({deleting.email})? This action cannot be undone.
          </p>
        )}
      </Modal>
    </div>
  );
}
