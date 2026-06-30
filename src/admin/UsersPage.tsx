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
  { value: "developer", label: "Developer" },
];

function roleFlags(role: string): { is_admin: boolean; is_developer: boolean } {
  return {
    is_admin: role === "admin" || role === "developer",
    is_developer: role === "developer",
  };
}

function roleValue(user: User): string {
  if (user.is_developer) return "developer";
  if (user.is_admin) return "admin";
  return "user";
}

function roleLabel(user: User): string {
  if (user.is_owner) return "Owner";
  if (user.is_developer) return "Developer";
  if (user.is_admin) return "Admin";
  return "User";
}

function formatIdentity(user: User): string {
  return user.domain ? `${user.domain}\\${user.username}` : user.username;
}

export default function UsersPage() {
  const { showSuccess, showError } = useSnackbar();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);

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
        ...roleFlags(role),
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

  const handleRoleChange = async (user: User, nextRole: string) => {
    if (user.is_owner) {
      return;
    }
    const currentRole = roleValue(user);
    if (nextRole === currentRole) {
      return;
    }

    setUpdatingUserId(user.id);
    try {
      const updated = await updateUser(user.id, roleFlags(nextRole));
      setUsers((current) =>
        current.map((item) => (item.id === user.id ? updated : item)),
      );
      showSuccess(`Updated ${user.display_name} to ${ROLE_OPTIONS.find((o) => o.value === nextRole)?.label ?? nextRole}.`);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to update user");
    } finally {
      setUpdatingUserId(null);
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
        description="Assign Developer to grant Admin → Diagnostics access. The machine owner always has developer access."
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
                      {user.is_owner ? (
                        <span className="badge badge--success">{roleLabel(user)}</span>
                      ) : (
                        <div className="users-table__role-select">
                          <Select
                            value={roleValue(user)}
                            onChange={(value) => void handleRoleChange(user, value)}
                            options={ROLE_OPTIONS}
                            size="sm"
                            fullWidth
                            disabled={updatingUserId === user.id}
                            aria-label={`Role for ${user.display_name}`}
                          />
                        </div>
                      )}
                    </td>
                    <td className="query-log-table__time">
                      {new Date(user.last_seen_at).toLocaleString()}
                    </td>
                    <td>
                      {!user.is_owner && (
                        <button
                          type="button"
                          className="btn btn--danger btn--sm"
                          onClick={() => void handleDelete(user)}
                        >
                          Delete
                        </button>
                      )}
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
