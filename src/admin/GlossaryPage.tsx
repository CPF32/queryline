import { useCallback, useEffect, useState } from "react";
import {
  createGlossaryTerm,
  deleteGlossaryTerm,
  listGlossaryTerms,
  updateGlossaryTerm,
} from "@/api/client";
import { useDataSourceContext, useRequiredDataSourceId } from "@/admin/DataSourceContext";
import PageHeader, {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/admin/AdminUi";
import type { GlossaryTerm } from "@/types/contracts";

interface TermForm {
  term: string;
  definition: string;
  sql_expression: string;
}

const EMPTY_FORM: TermForm = { term: "", definition: "", sql_expression: "" };

export default function GlossaryPage() {
  const dataSourceId = useRequiredDataSourceId();
  const { dataSource } = useDataSourceContext();

  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<TermForm>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTerms(await listGlossaryTerms(dataSourceId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load glossary");
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
    if (!form.term.trim() || !form.definition.trim()) return;
    setSaving(true);
    try {
      const body = {
        term: form.term.trim(),
        definition: form.definition.trim(),
        sql_expression: form.sql_expression.trim() || null,
      };
      if (editingId) {
        const updated = await updateGlossaryTerm(dataSourceId, editingId, body);
        setTerms((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      } else {
        const created = await createGlossaryTerm(dataSourceId, body);
        setTerms((prev) => [...prev, created]);
      }
      resetForm();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (term: GlossaryTerm) => {
    setEditingId(term.id);
    setForm({
      term: term.term,
      definition: term.definition,
      sql_expression: term.sql_expression ?? "",
    });
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this glossary term?")) return;
    try {
      await deleteGlossaryTerm(dataSourceId, id);
      setTerms((prev) => prev.filter((t) => t.id !== id));
      if (editingId === id) resetForm();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    }
  };

  return (
    <div className="page">
      <PageHeader
        title="Glossary"
        description={
          dataSource
            ? `Business terms for ${dataSource.name} mapped to SQL context.`
            : "Define business terms the LLM should understand."
        }
      />

      {loading && <LoadingState message="Loading glossary…" />}
      {error && !loading && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && (
        <div className="crud-layout">
          <form className="crud-form card" onSubmit={(e) => void handleSubmit(e)}>
            <h2 className="crud-form__title">
              {editingId ? "Edit term" : "Add term"}
            </h2>
            <label className="form-field">
              <span className="form-field__label">Term</span>
              <input
                className="form-field__input"
                value={form.term}
                onChange={(e) => setForm((f) => ({ ...f, term: e.target.value }))}
                required
              />
            </label>
            <label className="form-field">
              <span className="form-field__label">Definition</span>
              <textarea
                className="form-field__input form-field__textarea"
                rows={3}
                value={form.definition}
                onChange={(e) =>
                  setForm((f) => ({ ...f, definition: e.target.value }))
                }
                required
              />
            </label>
            <label className="form-field">
              <span className="form-field__label">SQL expression (optional)</span>
              <textarea
                className="form-field__input form-field__textarea code-input"
                rows={3}
                value={form.sql_expression}
                onChange={(e) =>
                  setForm((f) => ({ ...f, sql_expression: e.target.value }))
                }
                placeholder="EXISTS (SELECT 1 FROM …)"
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
            {terms.length === 0 ? (
              <EmptyState message="No glossary terms yet." />
            ) : (
              terms.map((term) => (
                <article key={term.id} className="card card--row">
                  <div className="card__main">
                    <h3 className="card__title">{term.term}</h3>
                    <p className="card__body">{term.definition}</p>
                    {term.sql_expression && (
                      <pre className="code-block">{term.sql_expression}</pre>
                    )}
                  </div>
                  <div className="card__actions">
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={() => startEdit(term)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn--danger btn--sm"
                      onClick={() => void handleDelete(term.id)}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
