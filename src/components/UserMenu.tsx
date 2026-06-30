import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import Icon, { type IconName } from "@/components/icons/Icon";
import { useAppUpdate } from "@/updates/AppUpdateContext";

function userInitial(user: { display_name?: string; username?: string } | null): string {
  const source = user?.display_name?.trim() || user?.username?.trim() || "?";
  return source.charAt(0).toUpperCase();
}

function userRoleLabel(user: { is_admin?: boolean; is_developer?: boolean } | null): string {
  if (user?.is_developer) return "Developer";
  return user?.is_admin ? "Administrator" : "User";
}

function MenuItemContent({ icon, label }: { icon: IconName; label: string }) {
  return (
    <>
      <Icon name={icon} size={16} className="user-menu__item-icon" aria-hidden />
      <span>{label}</span>
    </>
  );
}

interface UserMenuProps {
  placement?: "header" | "sidebar";
  expanded?: boolean;
}

export default function UserMenu({ placement = "header", expanded = false }: UserMenuProps) {
  const { user, loading, signedOut, signOut } = useAuth();
  const { currentVersion } = useAppUpdate();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const isSidebar = placement === "sidebar";
  const showSidebarIdentity = isSidebar && !expanded;

  useEffect(() => {
    if (!open) {
      return;
    }
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  if (loading) {
    if (isSidebar) {
      return (
        <div
          className={`user-menu user-menu--sidebar${expanded ? " user-menu--expanded" : ""}`}
          aria-hidden
        >
          <div className="user-menu__profile user-menu__profile--loading">
            <span className="user-menu__avatar user-menu__avatar--inline user-menu__avatar--loading" />
            <span
              className={`user-menu__profile-text${expanded ? "" : " user-menu__profile-text--collapsed"}`}
            >
              <span className="user-menu__profile-name">&nbsp;</span>
              <span className="user-menu__profile-role">&nbsp;</span>
            </span>
          </div>
        </div>
      );
    }
    return <div className="user-menu__avatar user-menu__avatar--loading" aria-hidden />;
  }

  if (signedOut || !user) {
    return null;
  }

  if (isSidebar) {
    return (
      <div
        className={`user-menu user-menu--sidebar${expanded ? " user-menu--expanded" : ""}`}
        ref={rootRef}
      >
        <button
          type="button"
          className="user-menu__profile"
          onClick={() => setOpen((current) => !current)}
          aria-expanded={open}
          aria-haspopup="menu"
          title={expanded ? undefined : user.display_name}
        >
          <span className="user-menu__avatar user-menu__avatar--inline" aria-hidden>
            {userInitial(user)}
          </span>
          <span
            className={`user-menu__profile-text${expanded ? "" : " user-menu__profile-text--collapsed"}`}
          >
            <span className="user-menu__profile-name">{user.display_name}</span>
            <span className="user-menu__profile-meta">
              <span className="user-menu__profile-role">{userRoleLabel(user)}</span>
              {currentVersion && (
                <span className="user-menu__profile-version">v{currentVersion}</span>
              )}
            </span>
          </span>
        </button>

        {open && (
          <div
            className={`user-menu__dropdown user-menu__dropdown--up${expanded ? " user-menu__dropdown--sidebar-expanded" : ""}`}
            role="menu"
          >
            {showSidebarIdentity && (
              <div className="user-menu__identity">
                <span className="user-menu__name">{user.display_name}</span>
                <span className="user-menu__meta">
                  {user.domain ? `${user.domain}\\${user.username}` : user.username}
                </span>
              </div>
            )}

            <div className="user-menu__options">
              <button
                type="button"
                className="user-menu__item"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  navigate("/");
                }}
              >
                <MenuItemContent icon="chat" label="Chat" />
              </button>

              <div className="user-menu__divider" role="separator" />

              {user.is_admin && (
                <>
                  <Link
                    to="/admin"
                    className="user-menu__item"
                    role="menuitem"
                    onClick={() => setOpen(false)}
                  >
                    <MenuItemContent icon="database" label="Admin" />
                  </Link>
                  <div className="user-menu__divider" role="separator" />
                </>
              )}

              <Link
                to="/settings"
                className="user-menu__item"
                role="menuitem"
                onClick={() => setOpen(false)}
              >
                <MenuItemContent icon="settings" label="Settings" />
              </Link>

              <div className="user-menu__divider" role="separator" />

              <button
                type="button"
                className="user-menu__item user-menu__sign-out"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  signOut();
                }}
              >
                <MenuItemContent icon="sign-out" label="Sign out" />
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="user-menu" ref={rootRef}>
      <button
        type="button"
        className="user-menu__avatar"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-haspopup="menu"
        title={user.display_name}
      >
        {userInitial(user)}
      </button>

      {open && (
        <div className="user-menu__dropdown" role="menu">
          <div className="user-menu__identity">
            <span className="user-menu__name">{user.display_name}</span>
            <span className="user-menu__meta">
              {user.domain ? `${user.domain}\\${user.username}` : user.username}
            </span>
          </div>

          <div className="user-menu__options">
            <button
              type="button"
              className="user-menu__item"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate("/");
              }}
            >
              <MenuItemContent icon="chat" label="Chat" />
            </button>

            <div className="user-menu__divider" role="separator" />

            {user.is_admin && (
              <>
                <Link
                  to="/admin"
                  className="user-menu__item"
                  role="menuitem"
                  onClick={() => setOpen(false)}
                >
                  <MenuItemContent icon="database" label="Admin" />
                </Link>
                <div className="user-menu__divider" role="separator" />
              </>
            )}

            <Link
              to="/settings"
              className="user-menu__item"
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              <MenuItemContent icon="settings" label="Settings" />
            </Link>

            <div className="user-menu__divider" role="separator" />

            <button
              type="button"
              className="user-menu__item user-menu__sign-out"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                signOut();
              }}
            >
              <MenuItemContent icon="sign-out" label="Sign out" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
