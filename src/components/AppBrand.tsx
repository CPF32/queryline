import { Link } from "react-router-dom";
import { clientTheme } from "@/theme/clientTheme.config";

interface AppBrandProps {
  to?: string;
  compact?: boolean;
  collapseText?: boolean;
  textCollapsed?: boolean;
  markSize?: number;
}

export default function AppBrand({
  to = "/",
  compact = false,
  collapseText = false,
  textCollapsed = false,
  markSize = 32,
}: AppBrandProps) {
  const { name, tagline, iconUrl } = clientTheme.brand;

  const brandClassName = [
    "app-brand",
    collapseText ? "app-brand--collapse-text" : "",
    collapseText && textCollapsed ? "app-brand--text-collapsed" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const content = (
    <>
      <span
        className="app-brand__mark"
        style={{ width: markSize, height: markSize }}
        aria-hidden
      >
        <img className="app-brand__icon" src={iconUrl} alt="" width={markSize} height={markSize} />
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
