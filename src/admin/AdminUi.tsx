import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export default function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header__text">
        <h1 className="page-header__title">{title}</h1>
        <p className="page-header__description">{description ?? "\u00A0"}</p>
      </div>
      <div className="page-header__actions">{actions ?? null}</div>
    </header>
  );
}

interface StatusBadgeProps {
  success: boolean | null | undefined;
  label?: string;
}

export function StatusBadge({ success, label }: StatusBadgeProps) {
  if (success === true) {
    return <span className="badge badge--success">{label ?? "Connected"}</span>;
  }
  if (success === false) {
    return <span className="badge badge--error">{label ?? "Failed"}</span>;
  }
  return <span className="badge badge--muted">{label ?? "Not tested"}</span>;
}

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "Loading…" }: LoadingStateProps) {
  return (
    <div className="state-panel state-panel--loading" role="status">
      <div className="spinner" aria-hidden />
      <p>{message}</p>
    </div>
  );
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="btn btn--secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  message: string;
  action?: ReactNode;
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="state-panel state-panel--empty">
      <p>{message}</p>
      {action}
    </div>
  );
}

interface AlertProps {
  variant: "success" | "error" | "info";
  message: string;
}

export function Alert({ variant, message }: AlertProps) {
  return <div className={`alert alert--${variant}`} role="alert">{message}</div>;
}
