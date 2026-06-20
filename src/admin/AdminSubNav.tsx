import Icon from "@/components/icons/Icon";
import { useEffect, useState } from "react";
import { NavLink, useParams } from "react-router-dom";
import { getDataSource } from "@/api/client";

const SUB_NAV_ITEMS = [
  { to: "schema", label: "Schema" },
  { to: "glossary", label: "Glossary" },
  { to: "examples", label: "Examples" },
  { to: "query-log", label: "Query Log" },
] as const;

export default function AdminSubNav() {
  const { dataSourceId } = useParams<{ dataSourceId?: string }>();
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    if (!dataSourceId) {
      setName(null);
      return;
    }

    let cancelled = false;
    void getDataSource(dataSourceId)
      .then((ds) => {
        if (!cancelled) setName(ds.name);
      })
      .catch(() => {
        if (!cancelled) setName(null);
      });

    return () => {
      cancelled = true;
    };
  }, [dataSourceId]);

  if (!dataSourceId) {
    return null;
  }

  return (
    <div className="admin-subnav">
      <div className="admin-subnav__context">
        <NavLink to="/admin" className="admin-subnav__back">
          <Icon name="arrow-left" size={14} />
          Sources
        </NavLink>
        <span className="admin-subnav__name">{name ?? "…"}</span>
      </div>
      <nav className="admin-subnav__tabs" aria-label="Data source sections">
        {SUB_NAV_ITEMS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={`/admin/data-sources/${dataSourceId}/${to}`}
            className={({ isActive }) =>
              `admin-subnav__tab${isActive ? " admin-subnav__tab--active" : ""}`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
