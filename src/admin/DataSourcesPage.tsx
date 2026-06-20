import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  deleteDataSource,
  listDataSources,
  testSavedConnection,
} from "@/api/client";
import PageHeader, {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/admin/AdminUi";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import { dataSourceTypeChips } from "@/utils/connectorLabels";
import type { DataSource } from "@/types/contracts";

export default function DataSourcesPage() {
  const navigate = useNavigate();
  const { showSuccess, showError } = useSnackbar();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<
    Record<string, { success: boolean; message: string }>
  >({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listDataSources();
      setSources(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data sources");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleTest = async (id: string, name: string) => {
    setTestingId(id);
    try {
      const result = await testSavedConnection(id);
      setTestResults((prev) => ({
        ...prev,
        [id]: { success: result.success, message: result.message },
      }));
      if (result.success) {
        showSuccess(result.message || `Connected to ${name} successfully.`);
      } else {
        showError(result.message || `Could not connect to ${name}.`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Test failed";
      setTestResults((prev) => ({
        ...prev,
        [id]: {
          success: false,
          message,
        },
      }));
      showError(message);
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Delete data source "${name}"? This cannot be undone.`)) {
      return;
    }
    try {
      await deleteDataSource(id);
      setSources((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const testStatus = (ds: DataSource) => {
    if (testResults[ds.id]) return testResults[ds.id].success;
    return ds.last_test_success;
  };

  return (
    <div className="page">
      <PageHeader
        title="Data Sources"
        description="Configure database connections for natural-language analytics."
        actions={
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => navigate("/admin/data-sources/new")}
          >
            Add data source
          </button>
        }
      />

      {loading && <LoadingState message="Loading data sources…" />}
      {error && !loading && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && sources.length === 0 && (
        <EmptyState
          message="No data sources configured yet."
          action={
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => navigate("/admin/data-sources/new")}
            >
              Add your first data source
            </button>
          }
        />
      )}

      {!loading && !error && sources.length > 0 && (
        <div className="card-list">
          {sources.map((ds) => {
            return (
              <article key={ds.id} className="card card--row">
                <div className="card__main">
                  <h2 className="card__title">
                    <Link to={`/admin/data-sources/${ds.id}/schema`}>{ds.name}</Link>
                  </h2>
                  <div className="card__meta">
                    {dataSourceTypeChips(ds.connector_type, ds.dialect_name).map((chip) => (
                      <span
                        key={chip.key}
                        className={`chip${chip.muted ? " chip--muted" : ""}`}
                      >
                        {chip.label}
                      </span>
                    ))}
                    {!ds.is_active && (
                      <span className="chip chip--warning">Inactive</span>
                    )}
                  </div>
                </div>
                <div className="card__actions">
                  <StatusBadge success={testStatus(ds)} />
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    disabled={testingId === ds.id}
                    onClick={() => void handleTest(ds.id, ds.name)}
                  >
                    {testingId === ds.id ? "Testing…" : "Test"}
                  </button>
                  <Link
                    to={`/admin/data-sources/${ds.id}/schema`}
                    className="btn btn--secondary btn--sm"
                  >
                    Manage
                  </Link>
                  <button
                    type="button"
                    className="btn btn--danger btn--sm"
                    onClick={() => void handleDelete(ds.id, ds.name)}
                  >
                    Delete
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
