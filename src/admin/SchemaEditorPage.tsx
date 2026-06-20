import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  createSchemaRelationship,
  deleteSchemaRelationship,
  listSchemaColumns,
  listSchemaRelationships,
  listSchemaTables,
  schemaObjectTypeLabel,
  updateSchemaColumn,
  updateSchemaTable,
} from "@/api/client";
import { useDataSourceContext, useRequiredDataSourceId } from "@/admin/DataSourceContext";
import PageHeader, {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/admin/AdminUi";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import Select from "@/components/Select";
import type { SchemaColumn, SchemaObjectType, SchemaRelationship, SchemaTable } from "@/types/contracts";

function tableLabel(t: SchemaTable): string {
  return t.schema_name ? `${t.schema_name}.${t.table_name}` : t.table_name;
}

function isQueryableType(objectType: SchemaObjectType | undefined): boolean {
  return !objectType || objectType === "table" || objectType === "view";
}

export default function SchemaEditorPage() {
  const { showSuccess, showError } = useSnackbar();
  const dataSourceId = useRequiredDataSourceId();
  const { dataSource } = useDataSourceContext();

  const [tables, setTables] = useState<SchemaTable[]>([]);
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null);
  const [columns, setColumns] = useState<SchemaColumn[]>([]);
  const [relationships, setRelationships] = useState<SchemaRelationship[]>([]);

  const [loadingTables, setLoadingTables] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [relForm, setRelForm] = useState({
    constraint_name: "",
    source_table_id: "",
    source_column_id: "",
    target_table_id: "",
    target_column_id: "",
  });
  const [relSaving, setRelSaving] = useState(false);

  const selectedTable = useMemo(
    () => tables.find((t) => t.id === selectedTableId) ?? null,
    [tables, selectedTableId],
  );

  const tableById = useMemo(
    () => new Map(tables.map((t) => [t.id, t])),
    [tables],
  );

  const columnById = useMemo(() => {
    const map = new Map<string, SchemaColumn>();
    for (const c of columns) map.set(c.id, c);
    return map;
  }, [columns]);

  const loadTables = useCallback(async () => {
    setLoadingTables(true);
    setError(null);
    try {
      const list = await listSchemaTables(dataSourceId);
      setTables(list);
      if (list.length > 0 && !selectedTableId) {
        setSelectedTableId(list[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tables");
    } finally {
      setLoadingTables(false);
    }
  }, [dataSourceId, selectedTableId]);

  const loadTableDetail = useCallback(
    async (tableId: string) => {
      setLoadingDetail(true);
      try {
        const [cols, rels] = await Promise.all([
          listSchemaColumns(dataSourceId, tableId),
          listSchemaRelationships(dataSourceId),
        ]);
        setColumns(cols.sort((a, b) => a.ordinal_position - b.ordinal_position));
        setRelationships(rels);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load table details");
      } finally {
        setLoadingDetail(false);
      }
    },
    [dataSourceId],
  );

  useEffect(() => {
    void loadTables();
  }, [loadTables]);

  useEffect(() => {
    if (selectedTableId) void loadTableDetail(selectedTableId);
  }, [selectedTableId, loadTableDetail]);

  const updateTableField = async (
    field: "description" | "display_name" | "is_included_in_prompt",
    value: string | boolean | null,
  ) => {
    if (!selectedTable) return;
    try {
      const updated = await updateSchemaTable(dataSourceId, selectedTable.id, {
        [field]: value,
      });
      setTables((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      showSuccess("Table saved.");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const updateColumnField = async (
    columnId: string,
    patch: Partial<{
      description: string | null;
      display_name: string | null;
      is_pii: boolean;
      is_excluded_from_prompt: boolean;
    }>,
  ) => {
    try {
      const updated = await updateSchemaColumn(dataSourceId, columnId, patch);
      setColumns((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      showSuccess("Column saved.");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const handleAddRelationship = async () => {
    if (
      !relForm.constraint_name ||
      !relForm.source_table_id ||
      !relForm.source_column_id ||
      !relForm.target_table_id ||
      !relForm.target_column_id
    ) {
      return;
    }
    setRelSaving(true);
    try {
      const rel = await createSchemaRelationship(dataSourceId, {
        ...relForm,
        relationship_type: "foreign_key",
      });
      setRelationships((prev) => [...prev, rel]);
      setRelForm({
        constraint_name: "",
        source_table_id: relForm.source_table_id,
        source_column_id: "",
        target_table_id: "",
        target_column_id: "",
      });
      showSuccess("Relationship added.");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to add relationship");
    } finally {
      setRelSaving(false);
    }
  };

  const handleDeleteRelationship = async (id: string) => {
    try {
      await deleteSchemaRelationship(dataSourceId, id);
      setRelationships((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      showError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const loadColumnsForTable = useCallback(
    async (tableId: string): Promise<SchemaColumn[]> => {
      if (tableId === selectedTableId) return columns;
      return listSchemaColumns(dataSourceId, tableId);
    },
    [columns, dataSourceId, selectedTableId],
  );

  const [sourceColumns, setSourceColumns] = useState<SchemaColumn[]>([]);
  const [targetColumns, setTargetColumns] = useState<SchemaColumn[]>([]);

  useEffect(() => {
    if (!relForm.source_table_id) {
      setSourceColumns([]);
      return;
    }
    void loadColumnsForTable(relForm.source_table_id).then(setSourceColumns);
  }, [relForm.source_table_id, loadColumnsForTable]);

  useEffect(() => {
    if (!relForm.target_table_id) {
      setTargetColumns([]);
      return;
    }
    void loadColumnsForTable(relForm.target_table_id).then(setTargetColumns);
  }, [relForm.target_table_id, loadColumnsForTable]);

  const tableRelationships = relationships.filter(
    (r) =>
      r.source_table_id === selectedTableId || r.target_table_id === selectedTableId,
  );

  return (
    <div className="page">
      <PageHeader
        title="Schema Editor"
        description={
          dataSource
            ? `Metadata for ${dataSource.name} (${dataSource.dialect_name})`
            : "Edit schema object metadata for the LLM prompt."
        }
        actions={
          <Link
            to={`/admin/data-sources/${dataSourceId}/schema/import`}
            className="btn btn--secondary"
          >
            Import more objects
          </Link>
        }
      />

      {loadingTables && <LoadingState message="Loading onboarded schema objects…" />}
      {error && !loadingTables && <ErrorState message={error} onRetry={loadTables} />}

      {!loadingTables && !error && tables.length === 0 && (
        <EmptyState
          message="No schema objects onboarded yet."
          action={
            <Link
              to={`/admin/data-sources/${dataSourceId}/schema/import`}
              className="btn btn--primary"
            >
              Import schema
            </Link>
          }
        />
      )}

      {!loadingTables && !error && tables.length > 0 && (
        <div className="schema-editor">
          <aside className="schema-editor__sidebar">
            <h2 className="schema-editor__sidebar-title">Schema objects</h2>
            <ul className="schema-editor__table-list">
              {tables.map((t) => {
                const objectType = t.object_type ?? "table";
                return (
                <li key={t.id}>
                  <button
                    type="button"
                    className={`schema-editor__table-btn${t.id === selectedTableId ? " schema-editor__table-btn--active" : ""}`}
                    onClick={() => setSelectedTableId(t.id)}
                  >
                    <span className="schema-editor__table-btn-label">{tableLabel(t)}</span>
                    <span className={`chip chip--type chip--type-${objectType}`}>
                      {schemaObjectTypeLabel(objectType)}
                    </span>
                    {!t.is_included_in_prompt && (
                      <span className="chip chip--warning">Excluded</span>
                    )}
                  </button>
                </li>
                );
              })}
            </ul>
          </aside>

          <div className="schema-editor__main">
            {loadingDetail && <LoadingState message="Loading columns…" />}

            {selectedTable && !loadingDetail && (
              <>
                <section className="editor-section">
                  <h3 className="editor-section__title">{tableLabel(selectedTable)}</h3>
                  <label className="form-field">
                    <span className="form-field__label">Description</span>
                    <textarea
                      className="form-field__input form-field__textarea"
                      rows={3}
                      defaultValue={selectedTable.description ?? ""}
                      onBlur={(e) =>
                        void updateTableField("description", e.target.value || null)
                      }
                    />
                  </label>
                  <label className="checkbox-field">
                    <input
                      type="checkbox"
                      checked={selectedTable.is_included_in_prompt}
                      onChange={(e) =>
                        void updateTableField("is_included_in_prompt", e.target.checked)
                      }
                    />
                    Include in LLM prompt
                  </label>
                  {(selectedTable.object_type === "function" ||
                    selectedTable.object_type === "procedure") && (
                    <>
                      {selectedTable.return_type && (
                        <p className="editor-section__meta">
                          Return type: <code>{selectedTable.return_type}</code>
                        </p>
                      )}
                      {selectedTable.definition && (
                        <label className="form-field">
                          <span className="form-field__label">Definition (read-only)</span>
                          <textarea
                            className="form-field__input form-field__textarea"
                            rows={6}
                            readOnly
                            value={selectedTable.definition}
                          />
                        </label>
                      )}
                    </>
                  )}
                </section>

                <section className="editor-section">
                  <h3 className="editor-section__title">
                    {selectedTable.object_type === "function" ||
                    selectedTable.object_type === "procedure"
                      ? "Parameters"
                      : "Columns"}
                  </h3>
                  <div className="column-grid">
                    {columns.map((col) => (
                      <article key={col.id} className="column-card">
                        <header className="column-card__header">
                          <strong>{col.column_name}</strong>
                          <span className="chip chip--muted">{col.data_type}</span>
                          {col.is_primary_key && (
                            <span className="chip">PK</span>
                          )}
                        </header>
                        <label className="form-field">
                          <span className="form-field__label">Description</span>
                          <input
                            className="form-field__input"
                            defaultValue={col.description ?? ""}
                            onBlur={(e) =>
                              void updateColumnField(col.id, {
                                description: e.target.value || null,
                              })
                            }
                          />
                        </label>
                        <div className="column-card__toggles">
                          <label className="checkbox-field">
                            <input
                              type="checkbox"
                              checked={col.is_pii ?? false}
                              onChange={(e) =>
                                void updateColumnField(col.id, {
                                  is_pii: e.target.checked,
                                })
                              }
                            />
                            PII
                          </label>
                          <label className="checkbox-field">
                            <input
                              type="checkbox"
                              checked={col.is_excluded_from_prompt ?? false}
                              onChange={(e) =>
                                void updateColumnField(col.id, {
                                  is_excluded_from_prompt: e.target.checked,
                                })
                              }
                            />
                            Exclude from prompt
                          </label>
                        </div>
                        {col.sample_distinct_values &&
                          col.sample_distinct_values.length > 0 && (
                            <div className="column-card__samples">
                              <span className="form-field__label">Sample values</span>
                              <div className="sample-chips">
                                {col.sample_distinct_values.map((v) => (
                                  <span key={v} className="chip">
                                    {v}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                      </article>
                    ))}
                  </div>
                </section>

                {isQueryableType(selectedTable.object_type) && (
                <section className="editor-section">
                  <h3 className="editor-section__title">Relationships</h3>
                  {tableRelationships.length === 0 ? (
                    <p className="muted">No relationships for this table.</p>
                  ) : (
                    <ul className="relationship-list">
                      {tableRelationships.map((r) => {
                        const srcTable = tableById.get(r.source_table_id);
                        const tgtTable = tableById.get(r.target_table_id);
                        const srcCol = columnById.get(r.source_column_id);
                        const tgtCol = columnById.get(r.target_column_id);
                        return (
                          <li key={r.id} className="relationship-list__item">
                            <span>
                              {srcTable ? tableLabel(srcTable) : r.source_table_id}.
                              {srcCol?.column_name ?? "?"} →{" "}
                              {tgtTable ? tableLabel(tgtTable) : r.target_table_id}.
                              {tgtCol?.column_name ?? "?"}
                            </span>
                            <button
                              type="button"
                              className="btn btn--danger btn--sm"
                              onClick={() => void handleDeleteRelationship(r.id)}
                            >
                              Remove
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}

                  <div className="relationship-form">
                    <h4>Add relationship</h4>
                    <div className="relationship-form__grid">
                      <label className="form-field">
                        <span className="form-field__label">Name</span>
                        <input
                          className="form-field__input"
                          value={relForm.constraint_name}
                          onChange={(e) =>
                            setRelForm((f) => ({
                              ...f,
                              constraint_name: e.target.value,
                            }))
                          }
                          placeholder="fk_orders_customer"
                        />
                      </label>
                      <label className="form-field">
                        <span className="form-field__label">Source table</span>
                        <Select
                          value={relForm.source_table_id}
                          onChange={(next) =>
                            setRelForm((f) => ({
                              ...f,
                              source_table_id: next,
                              source_column_id: "",
                            }))
                          }
                          placeholder="Select…"
                          options={tables.map((t) => ({
                            value: t.id,
                            label: tableLabel(t),
                          }))}
                          fullWidth
                        />
                      </label>
                      <label className="form-field">
                        <span className="form-field__label">Source column</span>
                        <Select
                          value={relForm.source_column_id}
                          onChange={(next) =>
                            setRelForm((f) => ({
                              ...f,
                              source_column_id: next,
                            }))
                          }
                          placeholder="Select…"
                          options={sourceColumns.map((c) => ({
                            value: c.id,
                            label: c.column_name,
                          }))}
                          fullWidth
                        />
                      </label>
                      <label className="form-field">
                        <span className="form-field__label">Target table</span>
                        <Select
                          value={relForm.target_table_id}
                          onChange={(next) =>
                            setRelForm((f) => ({
                              ...f,
                              target_table_id: next,
                              target_column_id: "",
                            }))
                          }
                          placeholder="Select…"
                          options={tables.map((t) => ({
                            value: t.id,
                            label: tableLabel(t),
                          }))}
                          fullWidth
                        />
                      </label>
                      <label className="form-field">
                        <span className="form-field__label">Target column</span>
                        <Select
                          value={relForm.target_column_id}
                          onChange={(next) =>
                            setRelForm((f) => ({
                              ...f,
                              target_column_id: next,
                            }))
                          }
                          placeholder="Select…"
                          options={targetColumns.map((c) => ({
                            value: c.id,
                            label: c.column_name,
                          }))}
                          fullWidth
                        />
                      </label>
                    </div>
                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      disabled={relSaving}
                      onClick={() => void handleAddRelationship()}
                    >
                      {relSaving ? "Adding…" : "Add relationship"}
                    </button>
                  </div>
                </section>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
