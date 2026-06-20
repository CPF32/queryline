import { useCallback, useEffect, useState } from "react";
import { createUser, deleteUser, listUsers, updateUser } from "@/api/client";
import PageHeader, {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/admin/AdminUi";
import Select from "@/components/Select";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import type { User } from "@/types/contracts";

const ROLE_OPTIONS = [
  { value: "user", label: "User" },
  { value: "admin", label: "Administrator" },
];

function formatIdentity(user: User): string {
  return user.domain ? `${user.domain}\\${user.username}` : user.username;
}

export default function UsersPage() {
  const { showSuccess, showError } = useSnackbar();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("user");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listUsers();
      setUsers(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setCreating(true);
    try {
      const created = await createUser({
        username: username.trim(),
        display_name: displayName.trim(),
        is_admin: role === "admin",
      });
      setUsers((current) =>
        [...current, created].sort((a, b) =>
          a.display_name.localeCompare(b.display_name),
        ),
      );
      setUsername("");
      setDisplayName("");
      setRole("user");
      showSuccess(`Added ${created.display_name}.`);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  const handleToggleAdmin = async (user: User) => {
    if (user.is_owner && user.is_admin) {
      showError("The machine owner account cannot be demoted.");
      return;
    }
    try {
      const updated = await updateUser(user.id, { is_admin: !user.is_admin });
      setUsers((current) =>
        current.map((item) => (item.id === user.id ? updated : item)),
      );
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to update user");
    }
  };

  const handleDelete = async (user: User) => {
    if (user.is_owner) {
      showError("The machine owner account cannot be deleted.");
      return;
    }
    if (!window.confirm(`Delete user "${user.display_name}"?`)) {
      return;
    }
    try {
      await deleteUser(user.id);
      setUsers((current) => current.filter((item) => item.id !== user.id));
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to delete user");
    }
  };

  return (
    <div className="page page--users">
      <PageHeader
        title="Users & roles"
        description="Provision users before their first sign-in and assign administrator access."
      />

      <section className="card settings-section users-add-section">
        <h2 className="settings-section__title">Add user</h2>
        <form className="user-form user-form--inline" onSubmit={handleCreate}>
          <label className="form-field form-field--compact form-field--username">
            <span className="form-field__label">Username</span>
            <input
              className="form-field__input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label className="form-field form-field--compact form-field--display-name">
            <span className="form-field__label">Display name</span>
            <input
              className="form-field__input"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
            />
          </label>
          <div className="form-field form-field--compact form-field--role">
            <span className="form-field__label">Role</span>
            <Select
              value={role}
              onChange={setRole}
              options={ROLE_OPTIONS}
              fullWidth
              size="sm"
              aria-label="Role"
            />
          </div>
          <button type="submit" className="btn btn--primary btn--sm" disabled={creating}>
            {creating ? "Adding…" : "Add user"}
          </button>
        </form>
      </section>

      <div className="users-list">
        {loading && <LoadingState message="Loading users…" />}
        {error && !loading && <ErrorState message={error} onRetry={load} />}

        {!loading && !error && users.length === 0 && (
          <EmptyState message="No users yet. Add one above or wait for first sign-in." />
        )}

        {!loading && !error && users.length > 0 && (
          <section className="card users-list__card">
            <div className="query-log-table-wrap users-table-wrap">
              <table className="query-log-table users-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Identity</th>
                  <th>Role</th>
                  <th>Last seen</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.display_name}</td>
                    <td>{formatIdentity(user)}</td>
                    <td>
                      <span className={`badge ${user.is_admin ? "badge--success" : "badge--muted"}`}>
                        {user.is_owner ? "Owner" : user.is_admin ? "Admin" : "User"}
                      </span>
                    </td>
                    <td className="query-log-table__time">
                      {new Date(user.last_seen_at).toLocaleString()}
                    </td>
                    <td>
                      <div className="btn-group">
                        {!user.is_owner && (
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            onClick={() => void handleToggleAdmin(user)}
                          >
                            {user.is_admin ? "Revoke admin" : "Make admin"}
                          </button>
                        )}
                        {!user.is_owner && (
                          <button
                            type="button"
                            className="btn btn--danger btn--sm"
                            onClick={() => void handleDelete(user)}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
