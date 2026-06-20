import { Link } from "react-router-dom";
import Icon from "@/components/icons/Icon";
import { clientTheme } from "@/theme/clientTheme.config";

interface AppBrandProps {
  to?: string;
  compact?: boolean;
  collapseText?: boolean;
  textCollapsed?: boolean;
}

export default function AppBrand({
  to = "/",
  compact = false,
  collapseText = false,
  textCollapsed = false,
}: AppBrandProps) {
  const { name, tagline } = clientTheme.brand;

  const brandClassName = [
    "app-brand",
    collapseText ? "app-brand--collapse-text" : "",
    collapseText && textCollapsed ? "app-brand--text-collapsed" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const content = (
    <>
      <span className="app-brand__mark" aria-hidden>
        <Icon name="brand" size={22} />
      </span>
      {(collapseText || !compact) && (
        <span className="app-brand__text">
          <span className="app-brand__name">{name}</span>
          <span className="app-brand__tag">{tagline}</span>
        </span>
      )}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={brandClassName}>
        {content}
      </Link>
    );
  }

  return <div className={brandClassName}>{content}</div>;
}
