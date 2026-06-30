import { NavLink } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";

const ADMIN_NAV_ITEMS = [
  { to: "/admin", label: "Data sources", end: true },
  { to: "/admin/llm-settings", label: "LLM", end: false },
  { to: "/admin/users", label: "Users", end: false },
] as const;

export default function AdminNav() {
  const { user } = useAuth();
  const items = user?.is_developer
    ? [
        ...ADMIN_NAV_ITEMS,
        { to: "/admin/diagnostic-logs", label: "Diagnostics", end: false },
      ]
    : [...ADMIN_NAV_ITEMS];

  return (
    <nav className="admin-nav" aria-label="Admin sections">
      {items.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `admin-nav__tab${isActive ? " admin-nav__tab--active" : ""}`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
