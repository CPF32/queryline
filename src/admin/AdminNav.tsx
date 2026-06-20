import { NavLink } from "react-router-dom";

const ADMIN_NAV_ITEMS = [
  { to: "/admin", label: "Data sources", end: true },
  { to: "/admin/llm-settings", label: "LLM", end: false },
  { to: "/admin/users", label: "Users", end: false },
] as const;

export default function AdminNav() {
  return (
    <nav className="admin-nav" aria-label="Admin sections">
      {ADMIN_NAV_ITEMS.map(({ to, label, end }) => (
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
