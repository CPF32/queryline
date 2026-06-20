import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { importSchema, introspectSchema, schemaObjectKey, schemaObjectTypeLabel } from "@/api/client";
import { useRequiredDataSourceId } from "@/admin/DataSourceContext";
import PageHeader, { ErrorState, LoadingState } from "@/admin/AdminUi";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import type { SchemaObjectType, SchemaTableDraft } from "@/types/contracts";

type Phase = "idle" | "introspecting" | "selecting" | "importing" | "done";
type FilterType = "all" | SchemaObjectType;

const OBJECT_TYPES: SchemaObjectType[] = ["table", "view", "function", "procedure"];

function objectKey(draft: SchemaTableDraft): string {
  return schemaObjectKey(
    draft.schema_name,
    draft.table_name,
    draft.object_type ?? "table",
  );
}

export default function ImportSchemaFlow() {
  const dataSourceId = useRequiredDataSourceId();
  const navigate = useNavigate();
  const { showSuccess, showError } = useSnackbar();

  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [objects, setObjects] = useState<SchemaTableDraft[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [typeFilter, setTypeFilter] = useState<FilterType>("all");
  const [importResult, setImportResult] = useState<{
    tables_imported: number;
    columns_imported: number;
    relationships_imported: number;
  } | null>(null);

  const countsByType = useMemo(() => {
    const counts: Record<SchemaObjectType, number> = {
      table: 0,
      view: 0,
      function: 0,
      procedure: 0,
    };
    for (const obj of objects) {
      const type = obj.object_type ?? "table";
      counts[type] += 1;
    }
    return counts;
  }, [objects]);

  const objectEntries = useMemo(
    () =>
      objects.map((draft) => ({
        key: objectKey(draft),
        draft,
        columnCount: draft.columns.length,
        relationshipCount: draft.relationships.length,
      })),
    [objects],
  );

  const filteredEntries = useMemo(() => {
    if (typeFilter === "all") {
      return objectEntries;
    }
    return objectEntries.filter(
      (entry) => (entry.draft.object_type ?? "table") === typeFilter,
    );
  }, [objectEntries, typeFilter]);

  const startIntrospect = useCallback(async () => {
    setPhase("introspecting");
    setError(null);
    setImportResult(null);
    try {
      const snapshot = await introspectSchema(dataSourceId);
      setObjects(snapshot.tables);
      setSelected(new Set(snapshot.tables.map((t) => objectKey(t))));
      setPhase("selecting");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Schema introspection failed");
      setPhase("idle");
    }
  }, [dataSourceId]);

  useEffect(() => {
    void startIntrospect();
  }, [startIntrospect]);

  useEffect(() => {
    if (phase !== "done" || !importResult) {
      return;
    }
    showSuccess(
      `Imported ${importResult.tables_imported} objects, ${importResult.columns_imported} columns/parameters, and ${importResult.relationships_imported} relationships.`,
    );
  }, [phase, importResult, showSuccess]);

  const toggleObject = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleAllVisible = (checked: boolean) => {
    if (checked) {
      setSelected((prev) => {
        const next = new Set(prev);
        for (const entry of filteredEntries) {
          next.add(entry.key);
        }
        return next;
      });
    } else {
      setSelected((prev) => {
        const next = new Set(prev);
        for (const entry of filteredEntries) {
          next.delete(entry.key);
        }
        return next;
      });
    }
  };

  const allVisibleSelected =
    filteredEntries.length > 0 &&
    filteredEntries.every((entry) => selected.has(entry.key));

  const handleImport = async () => {
    if (selected.size === 0) return;
    setPhase("importing");
    try {
      const result = await importSchema(dataSourceId, {
        mode: "merge",
        include_tables: Array.from(selected),
      });
      setImportResult(result);
      setPhase("done");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Schema import failed");
      setPhase("selecting");
    }
  };

  return (
    <div className="page">
      <PageHeader
        title="Import Schema"
        description="Discover tables, views, functions, and procedures from the live database and choose which to onboard."
        actions={
          <Link
            to={`/admin/data-sources/${dataSourceId}/schema`}
            className="btn btn--secondary"
          >
            Skip to editor
          </Link>
        }
      />

      {phase === "introspecting" && (
        <LoadingState message="Introspecting database schema — this may take a while…" />
      )}

      {error && phase !== "introspecting" && (
        <ErrorState message={error} onRetry={startIntrospect} />
      )}

      {phase === "selecting" && !error && (
        <section className="import-panel">
          <div className="import-panel__type-tabs">
            <button
              type="button"
              className={`import-panel__type-tab${typeFilter === "all" ? " import-panel__type-tab--active" : ""}`}
              onClick={() => setTypeFilter("all")}
            >
              All ({objects.length})
            </button>
            {OBJECT_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                className={`import-panel__type-tab${typeFilter === type ? " import-panel__type-tab--active" : ""}`}
                onClick={() => setTypeFilter(type)}
              >
                {schemaObjectTypeLabel(type)}s ({countsByType[type]})
              </button>
            ))}
          </div>

          <div className="import-panel__toolbar">
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={allVisibleSelected}
                onChange={(e) => toggleAllVisible(e.target.checked)}
              />
              Select all visible ({filteredEntries.length})
            </label>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => void startIntrospect()}
            >
              Re-scan
            </button>
          </div>

          {objectEntries.length === 0 ? (
            <p className="inline-notice">No schema objects discovered in this database.</p>
          ) : filteredEntries.length === 0 ? (
            <p className="inline-notice">
              {`No ${typeFilter === "all" ? "objects" : `${schemaObjectTypeLabel(typeFilter).toLowerCase()}s`} match this filter.`}
            </p>
          ) : (
            <ul className="import-checklist">
              {filteredEntries.map(({ key, draft, columnCount, relationshipCount }) => {
                const objectType = draft.object_type ?? "table";
                const isRoutine = objectType === "function" || objectType === "procedure";
                return (
                  <li key={key} className="import-checklist__item">
                    <label className="import-checklist__label">
                      <input
                        type="checkbox"
                        checked={selected.has(key)}
                        onChange={() => toggleObject(key)}
                      />
                      <span className="import-checklist__name">
                        {draft.schema_name
                          ? `${draft.schema_name}.${draft.table_name}`
                          : draft.table_name}
                      </span>
                      <span className={`chip chip--type chip--type-${objectType}`}>
                        {schemaObjectTypeLabel(objectType)}
                      </span>
                    </label>
                    <span className="import-checklist__meta">
                      {isRoutine
                        ? `${columnCount} parameter${columnCount !== 1 ? "s" : ""}`
                        : `${columnCount} column${columnCount !== 1 ? "s" : ""}`}
                      {relationshipCount > 0 && (
                        <> · {relationshipCount} relationship{relationshipCount !== 1 ? "s" : ""}</>
                      )}
                      {draft.row_count_estimate != null && (
                        <> · ~{draft.row_count_estimate.toLocaleString()} rows</>
                      )}
                      {draft.return_type && <> · returns {draft.return_type}</>}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}

          <div className="wizard-actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={selected.size === 0}
              onClick={() => void handleImport()}
            >
              Import {selected.size} object{selected.size !== 1 ? "s" : ""}
            </button>
          </div>
        </section>
      )}

      {phase === "importing" && (
        <LoadingState message="Importing selected schema objects…" />
      )}

      {phase === "done" && importResult && (
        <section className="import-panel">
          <div className="wizard-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => navigate(`/admin/data-sources/${dataSourceId}/schema`)}
            >
              Open schema editor
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
