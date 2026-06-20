import { useCallback, useEffect, useState } from "react";
import {
  createExample,
  deleteExample,
  executeSql,
  listExamples,
  updateExample,
} from "@/api/client";
import { useDataSourceContext, useRequiredDataSourceId } from "@/admin/DataSourceContext";
import PageHeader, {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/admin/AdminUi";
import DataTable from "@/components/DataTable";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import type { SqlExample } from "@/types/contracts";
import type { QueryResult } from "@/types/contracts";

interface ExampleForm {
  question: string;
  sql: string;
  notes: string;
}

const EMPTY_FORM: ExampleForm = { question: "", sql: "", notes: "" };

function newSessionId(): string {
  return crypto.randomUUID();
}

export default function ExamplesPage() {
  const dataSourceId = useRequiredDataSourceId();
  const { dataSource } = useDataSourceContext();
  const { showError } = useSnackbar();

  const [examples, setExamples] = useState<SqlExample[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<ExampleForm>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<
    Record<string, { result?: QueryResult; error?: string }>
  >({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setExamples(await listExamples(dataSourceId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load examples");
    } finally {
      setLoading(false);
    }
  }, [dataSourceId]);

  useEffect(() => {
    void load();
  }, [load]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.question.trim() || !form.sql.trim()) return;
    setSaving(true);
    try {
      const body = {
        question: form.question.trim(),
        sql: form.sql.trim(),
        notes: form.notes.trim() || null,
      };
      if (editingId) {
        const updated = await updateExample(dataSourceId, editingId, body);
        setExamples((prev) => prev.map((ex) => (ex.id === updated.id ? updated : ex)));
      } else {
        const created = await createExample(dataSourceId, body);
        setExamples((prev) => [...prev, created]);
      }
      resetForm();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (ex: SqlExample) => {
    setEditingId(ex.id);
    setForm({
      question: ex.question,
      sql: ex.sql,
      notes: ex.notes ?? "",
    });
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this example?")) return;
    try {
      await deleteExample(dataSourceId, id);
      setExamples((prev) => prev.filter((ex) => ex.id !== id));
      if (editingId === id) resetForm();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const handleTest = async (ex: SqlExample) => {
    setTestingId(ex.id);
    setTestResults((prev) => ({ ...prev, [ex.id]: {} }));
    try {
      const { query_result } = await executeSql({
        data_source_id: dataSourceId,
        session_id: newSessionId(),
        sql: ex.sql,
        user_question: ex.question,
        max_rows: 100,
        timeout_seconds: 30,
      });
      setTestResults((prev) => ({
        ...prev,
        [ex.id]: { result: query_result },
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Execution failed";
      showError(message);
      setTestResults((prev) => ({
        ...prev,
        [ex.id]: { error: message },
      }));
    } finally {
      setTestingId(null);
    }
  };

  return (
    <div className="page">
      <PageHeader
        title="SQL Examples"
        description={
          dataSource
            ? `Few-shot examples for ${dataSource.name}. Test runs SQL through the live execution pipeline.`
            : "Question/SQL pairs for few-shot prompting."
        }
      />

      {loading && <LoadingState message="Loading examples…" />}
      {error && !loading && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && (
        <div className="crud-layout">
          <form className="crud-form card" onSubmit={(e) => void handleSubmit(e)}>
            <h2 className="crud-form__title">
              {editingId ? "Edit example" : "Add example"}
            </h2>
            <label className="form-field">
              <span className="form-field__label">Question</span>
              <textarea
                className="form-field__input form-field__textarea"
                rows={2}
                value={form.question}
                onChange={(e) =>
                  setForm((f) => ({ ...f, question: e.target.value }))
                }
                required
              />
            </label>
            <label className="form-field">
              <span className="form-field__label">SQL</span>
              <textarea
                className="form-field__input form-field__textarea code-input"
                rows={5}
                value={form.sql}
                onChange={(e) => setForm((f) => ({ ...f, sql: e.target.value }))}
                required
              />
            </label>
            <label className="form-field">
              <span className="form-field__label">Notes (optional)</span>
              <input
                className="form-field__input"
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              />
            </label>
            <div className="crud-form__actions">
              <button type="submit" className="btn btn--primary" disabled={saving}>
                {saving ? "Saving…" : editingId ? "Update" : "Create"}
              </button>
              {editingId && (
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={resetForm}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>

          <div className="crud-list">
            {examples.length === 0 ? (
              <EmptyState message="No SQL examples yet." />
            ) : (
              examples.map((ex) => {
                const test = testResults[ex.id];
                return (
                <article key={ex.id} className="card">
                  <div className="card__main">
                    <h3 className="card__title">{ex.question}</h3>
                    <pre className="code-block">{ex.sql}</pre>
                    {ex.notes && <p className="card__body muted">{ex.notes}</p>}
                  </div>
                  <div className="card__actions">
                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      disabled={testingId === ex.id}
                      onClick={() => void handleTest(ex)}
                    >
                      {testingId === ex.id ? "Running…" : "Test this example"}
                    </button>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={() => startEdit(ex)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn--danger btn--sm"
                      onClick={() => void handleDelete(ex.id)}
                    >
                      Delete
                    </button>
                  </div>
                  {testingId === ex.id && (
                    <LoadingState message="Executing SQL through live pipeline…" />
                  )}
                  {test?.result && (
                    <div className="test-result">
                      <p className="muted">
                        {test.result.row_count} row(s) in{" "}
                        {test.result.execution_ms.toFixed(0)} ms
                      </p>
                      <DataTable
                        columns={test.result.columns}
                        rows={test.result.rows}
                        truncated={test.result.truncated}
                      />
                    </div>
                  )}
                </article>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
