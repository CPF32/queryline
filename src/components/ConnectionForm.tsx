import { useCallback, useMemo } from "react";
import type { ConnectionFormSchema } from "@/types/contracts";
import Select from "@/components/Select";
import { isMaskedPassword } from "@/utils/schemaValidation";

export interface ConnectionFormProps {
  schema: ConnectionFormSchema;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  errors?: Record<string, string>;
  disabled?: boolean;
}

function inputType(prop: ConnectionFormSchema["properties"][string]): string {
  if (prop.format === "password") return "password";
  if (prop.type === "integer" || prop.type === "number") return "number";
  return "text";
}

export default function ConnectionForm({
  schema,
  values,
  onChange,
  errors = {},
  disabled = false,
}: ConnectionFormProps) {
  const fields = useMemo(
    () => Object.entries(schema.properties ?? {}),
    [schema.properties],
  );

  const setField = useCallback(
    (key: string, raw: string | number | boolean) => {
      const prop = schema.properties[key];
      let value: unknown = raw;
      if (prop?.type === "integer") {
        value = raw === "" ? "" : parseInt(String(raw), 10);
      } else if (prop?.type === "number") {
        value = raw === "" ? "" : parseFloat(String(raw));
      }
      onChange({ ...values, [key]: value });
    },
    [onChange, schema.properties, values],
  );

  return (
    <div className="connection-form">
      {schema.title && <h3 className="connection-form__title">{schema.title}</h3>}
      {fields.map(([key, prop]) => {
        const error = errors[key];
        const label = prop.title ?? key;
        const current = values[key];

        if (prop.enum && prop.enum.length > 0) {
          const enumOptions = prop.enum.map((opt) => ({ value: opt, label: opt }));
          return (
            <label key={key} className="form-field">
              <span className="form-field__label">{label}</span>
              <Select
                className={error ? "app-select--error" : ""}
                value={current != null ? String(current) : ""}
                onChange={(next) => setField(key, next)}
                disabled={disabled}
                placeholder="Select…"
                options={enumOptions}
                fullWidth
              />
              {prop.description && (
                <span className="form-field__hint">{prop.description}</span>
              )}
              {error && <span className="form-field__error">{error}</span>}
            </label>
          );
        }

        if (prop.format === "file") {
          const canBrowse = typeof window.desktopApp?.pickSqliteFile === "function";
          const pathValue = current != null ? String(current) : "";

          return (
            <label key={key} className="form-field">
              <span className="form-field__label">{label}</span>
              <div className="file-path-field">
                <input
                  type="text"
                  className={`form-field__input file-path-field__input${error ? " form-field__input--error" : ""}`}
                  value={pathValue}
                  onChange={(e) => setField(key, e.target.value)}
                  placeholder="/absolute/path/to/database.sqlite"
                  disabled={disabled}
                  spellCheck={false}
                  autoComplete="off"
                />
                {canBrowse && (
                  <button
                    type="button"
                    className="btn btn--secondary file-path-field__browse"
                    disabled={disabled}
                    onClick={() => {
                      void window.desktopApp?.pickSqliteFile?.().then((picked) => {
                        if (picked) setField(key, picked);
                      });
                    }}
                  >
                    Browse…
                  </button>
                )}
              </div>
              {prop.description && (
                <span className="form-field__hint">{prop.description}</span>
              )}
              {!canBrowse && (
                <span className="form-field__hint">
                  Paste the full absolute path (e.g.{" "}
                  <code>/Users/you/project/sqlite_databases/databases/retail.sqlite</code>
                  ). Browser file pickers cannot expose file locations.
                </span>
              )}
              {error && <span className="form-field__error">{error}</span>}
            </label>
          );
        }

        const masked = prop.format === "password" && isMaskedPassword(current);

        return (
          <label key={key} className="form-field">
            <span className="form-field__label">{label}</span>
            <input
              type={inputType(prop)}
              className={`form-field__input${error ? " form-field__input--error" : ""}`}
              value={masked ? "" : current != null ? String(current) : ""}
              placeholder={masked ? "•••••••• (unchanged)" : undefined}
              onChange={(e) => setField(key, e.target.value)}
              disabled={disabled}
              autoComplete={prop.format === "password" ? "new-password" : "off"}
            />
            {prop.description && (
              <span className="form-field__hint">{prop.description}</span>
            )}
            {error && <span className="form-field__error">{error}</span>}
          </label>
        );
      })}
    </div>
  );
}
