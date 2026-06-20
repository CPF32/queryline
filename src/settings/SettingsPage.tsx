import { useEffect, useRef, useState } from "react";
import { updateCurrentUserProfile, updateUser } from "@/api/client";
import Select from "@/components/Select";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/auth/AuthContext";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import { normalizeTheme } from "@/theme/ThemeSync";
import { useTheme, type Theme } from "@/theme/ThemeProvider";

const ROLE_OPTIONS = [
  { value: "user", label: "User" },
  { value: "admin", label: "Administrator" },
];

export default function SettingsPage() {
  const { user, updateUser: setAuthUser } = useAuth();
  const { setTheme } = useTheme();
  const { showSuccess, showError } = useSnackbar();
  const isAdmin = Boolean(user?.is_admin);
  const isOwner = Boolean(user?.is_owner);
  const savedThemeRef = useRef<Theme>("dark");

  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [isAdminRole, setIsAdminRole] = useState(false);
  const [theme, setThemeDraft] = useState<Theme>("dark");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const savedTheme = normalizeTheme(user?.theme);
    savedThemeRef.current = savedTheme;
    setDisplayName(user?.display_name ?? "");
    setUsername(user?.username ?? "");
    setIsAdminRole(Boolean(user?.is_admin));
    setThemeDraft(savedTheme);
  }, [user?.display_name, user?.is_admin, user?.theme, user?.username]);

  useEffect(() => {
    return () => {
      setTheme(savedThemeRef.current);
    };
  }, [setTheme]);

  const profileDirty =
    Boolean(user) &&
    (displayName.trim() !== (user?.display_name ?? "").trim() ||
      theme !== normalizeTheme(user?.theme) ||
      (isAdmin &&
        (username.trim() !== (user?.username ?? "").trim() ||
          isAdminRole !== Boolean(user?.is_admin))));

  const handleThemeChange = (next: Theme) => {
    setThemeDraft(next);
    setTheme(next);
  };

  const handleProfileSave = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedDisplayName = displayName.trim();
    const trimmedUsername = username.trim();
    if (!trimmedDisplayName || !profileDirty || !user) {
      return;
    }

    setSaving(true);
    try {
      const updated = isAdmin
        ? await updateUser(user.id, {
            display_name: trimmedDisplayName,
            username: trimmedUsername,
            is_admin: isAdminRole,
            theme,
          })
        : await updateCurrentUserProfile({
            display_name: trimmedDisplayName,
            theme,
          });
      savedThemeRef.current = normalizeTheme(updated.theme);
      setAuthUser(updated);
      setDisplayName(updated.display_name);
      setUsername(updated.username);
      setIsAdminRole(updated.is_admin);
      setThemeDraft(normalizeTheme(updated.theme));
      setTheme(normalizeTheme(updated.theme));
      showSuccess("Profile saved.");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-page__panel">
        <header className="settings-page__header">
          <h1 className="settings-page__title">Settings</h1>
        </header>

        <section className="card settings-card">
          <form className="settings-card__form" onSubmit={handleProfileSave}>
            <div className="settings-card__rows">
              <label className="settings-row">
                <span className="settings-row__label">Display name</span>
                <input
                  className="form-field__input settings-row__control"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Your name"
                  required
                />
              </label>

              <label className="settings-row">
                <span className="settings-row__label">Username</span>
                <input
                  className="form-field__input settings-row__control"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  disabled={!isAdmin}
                />
              </label>

              <div className="settings-row">
                <span className="settings-row__label">Role</span>
                <Select
                  className="settings-row__control"
                  value={isOwner || isAdminRole ? "admin" : "user"}
                  onChange={(next) => setIsAdminRole(next === "admin")}
                  options={
                    isOwner
                      ? [{ value: "admin", label: "Owner (machine administrator)" }]
                      : ROLE_OPTIONS
                  }
                  disabled={!isAdmin || isOwner}
                  fullWidth
                />
              </div>

              <div className="settings-row">
                <span className="settings-row__label">Theme</span>
                <div className="settings-row__control settings-row__control--toggle">
                  <ThemeToggle variant="switch" value={theme} onChange={handleThemeChange} />
                </div>
              </div>
            </div>

            <div className="settings-card__footer">
              <button
                type="submit"
                className="btn btn--primary btn--sm"
                disabled={saving || !profileDirty || !displayName.trim() || (isAdmin && !username.trim())}
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
