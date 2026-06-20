import { Fragment, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createExample, listQueryLog } from "@/api/client";
import { useDataSourceContext, useRequiredDataSourceId } from "@/admin/DataSourceContext";
import PageHeader, {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/admin/AdminUi";
import type { QueryLogEntry } from "@/types/contracts";

const PAGE_SIZE = 20;

function statusSuccess(status: QueryLogEntry["execution_status"]): boolean | null {
  if (status === "success") return true;
  if (status === "validation_error" || status === "execution_error") return false;
  return null;
}

export default function QueryLogPage() {
  const dataSourceId = useRequiredDataSourceId();
  const { dataSource } = useDataSourceContext();
  const navigate = useNavigate();

  const [entries, setEntries] = useState<QueryLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [promotingId, setPromotingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listQueryLog(dataSourceId, {
        limit: PAGE_SIZE,
        offset,
      });
      setEntries(res.data);
      setTotal(res.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load query log");
    } finally {
      setLoading(false);
    }
  }, [dataSourceId, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  const handlePromote = async (entry: QueryLogEntry) => {
    setPromotingId(entry.id);
    try {
      await createExample(dataSourceId, {
        question: entry.user_question,
        sql: entry.generated_sql,
        notes: `Promoted from query log ${entry.id}`,
      });
      navigate(`/admin/data-sources/${dataSourceId}/examples`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Promote failed");
    } finally {
      setPromotingId(null);
    }
  };

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="page">
      <PageHeader
        title="Query Log"
        description={
          dataSource
            ? `Past generated queries for ${dataSource.name}.`
            : "Review generated SQL and promote successful queries to examples."
        }
      />

      {loading && <LoadingState message="Loading query log…" />}
      {error && !loading && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && entries.length === 0 && (
        <EmptyState message="No queries logged yet." />
      )}

      {!loading && !error && entries.length > 0 && (
        <>
          <div className="query-log-table-wrap">
            <table className="data-table query-log-table">
              <thead>
                <tr>
                  <th aria-label="Expand" />
                  <th>Time</th>
                  <th>Question</th>
                  <th>Status</th>
                  <th>Rows</th>
                  <th>Duration</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const expanded = expandedId === entry.id;
                  return (
                    <Fragment key={entry.id}>
                      <tr>
                        <td>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            aria-expanded={expanded}
                            onClick={() =>
                              setExpandedId(expanded ? null : entry.id)
                            }
                          >
                            {expanded ? "▼" : "▶"}
                          </button>
                        </td>
                        <td className="query-log-table__time">
                          {new Date(entry.created_at).toLocaleString()}
                        </td>
                        <td className="query-log-table__question">
                          {entry.user_question}
                        </td>
                        <td>
                          <StatusBadge
                            success={statusSuccess(entry.execution_status)}
                            label={entry.execution_status.replace("_", " ")}
                          />
                        </td>
                        <td>{entry.row_count ?? "—"}</td>
                        <td>
                          {entry.execution_ms != null
                            ? `${entry.execution_ms.toFixed(0)} ms`
                            : "—"}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            disabled={promotingId === entry.id}
                            onClick={() => void handlePromote(entry)}
                          >
                            {promotingId === entry.id
                              ? "Promoting…"
                              : "Promote to example"}
                          </button>
                        </td>
                      </tr>
                      {expanded && (
                        <tr className="query-log-detail">
                          <td colSpan={7}>
                            <pre className="code-block">{entry.generated_sql}</pre>
                            {entry.error_message && (
                              <p className="query-log-detail__error">
                                {entry.error_message}
                              </p>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
            >
              Previous
            </button>
            <span className="pagination__info">
              Page {page} of {totalPages} ({total} total)
            </span>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset((o) => o + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
