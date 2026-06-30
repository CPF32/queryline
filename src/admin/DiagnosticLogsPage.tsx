import { Fragment, useCallback, useEffect, useState } from "react";
import { clearDiagnosticLogs, listDiagnosticLogs } from "@/api/client";
import PageHeader, {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/admin/AdminUi";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import type { DiagnosticLogEntry } from "@/types/contracts";

const PAGE_SIZE = 25;

const LEVEL_OPTIONS = [
  { value: "", label: "All levels" },
  { value: "error", label: "Error" },
  { value: "warning", label: "Warning" },
  { value: "info", label: "Info" },
];

function levelClass(level: DiagnosticLogEntry["level"]): string {
  if (level === "error") return "badge badge--error";
  if (level === "warning") return "badge badge--muted";
  return "badge badge--muted";
}

export default function DiagnosticLogsPage() {
  const { showSuccess, showError } = useSnackbar();
  const [entries, setEntries] = useState<DiagnosticLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [level, setLevel] = useState("");
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listDiagnosticLogs({
        limit: PAGE_SIZE,
        offset,
        level: level || undefined,
      });
      setEntries(res.data);
      setTotal(res.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load diagnostic logs");
    } finally {
      setLoading(false);
    }
  }, [level, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleClear = async () => {
    if (!window.confirm("Clear all diagnostic log entries? This cannot be undone.")) {
      return;
    }
    setClearing(true);
    try {
      const result = await clearDiagnosticLogs();
      setOffset(0);
      setExpandedId(null);
      await load();
      showSuccess(`Cleared ${result.deleted} log ${result.deleted === 1 ? "entry" : "entries"}.`);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to clear logs");
    } finally {
      setClearing(false);
    }
  };

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="page page--diagnostic-logs">
      <PageHeader
        title="Diagnostic logs"
        description="Underlying server and client errors for troubleshooting. Visible to developers only."
        actions={
          <div className="btn-group">
            <label className="form-field form-field--compact">
              <span className="form-field__label">Level</span>
              <select
                className="form-field__input"
                value={level}
                onChange={(event) => {
                  setLevel(event.target.value);
                  setOffset(0);
                }}
              >
                {LEVEL_OPTIONS.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => void load()}
              disabled={loading}
            >
              Refresh
            </button>
            <button
              type="button"
              className="btn btn--danger btn--sm"
              onClick={() => void handleClear()}
              disabled={clearing || loading || total === 0}
            >
              {clearing ? "Clearing…" : "Clear all"}
            </button>
          </div>
        }
      />

      {loading && <LoadingState message="Loading diagnostic logs…" />}
      {error && !loading && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && entries.length === 0 && (
        <EmptyState message="No diagnostic log entries yet. Errors from chat, LLM calls, and the API will appear here." />
      )}

      {!loading && !error && entries.length > 0 && (
        <section className="card">
          <div className="query-log-table-wrap">
            <table className="query-log-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Level</th>
                  <th>Source</th>
                  <th>Message</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <Fragment key={entry.id}>
                    <tr>
                      <td className="query-log-table__time">
                        {new Date(entry.created_at).toLocaleString()}
                      </td>
                      <td>
                        <span className={levelClass(entry.level)}>{entry.level}</span>
                      </td>
                      <td>
                        <code>{entry.source}</code>
                      </td>
                      <td className="diagnostic-log__message">{entry.message}</td>
                      <td>
                        {entry.details && (
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() =>
                              setExpandedId((current) =>
                                current === entry.id ? null : entry.id,
                              )
                            }
                          >
                            {expandedId === entry.id ? "Hide" : "Details"}
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedId === entry.id && entry.details && (
                      <tr className="diagnostic-log__details-row">
                        <td colSpan={5}>
                          <pre className="diagnostic-log__details">
                            {JSON.stringify(entry.details, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                disabled={offset === 0}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
              >
                Previous
              </button>
              <span className="pagination__label">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
              >
                Next
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
