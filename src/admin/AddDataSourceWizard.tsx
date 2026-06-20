import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createDataSource,
  getConnectionFormSchema,
  getConnectors,
  testConnection,
} from "@/api/client";
import PageHeader, { LoadingState } from "@/admin/AdminUi";
import ConnectionForm from "@/components/ConnectionForm";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import { formatConnectorLabel } from "@/utils/connectorLabels";
import type { ConnectionFormSchema, ConnectionTestResult, ConnectorInfo } from "@/types/contracts";
import {
  applySchemaDefaults,
  hasValidationErrors,
  validateConnectionConfig,
} from "@/utils/schemaValidation";

const STEPS = ["Engine", "Connection", "Test", "Save"] as const;

export default function AddDataSourceWizard() {
  const navigate = useNavigate();
  const { showSuccess, showError } = useSnackbar();
  const [step, setStep] = useState(0);

  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [connectorsLoading, setConnectorsLoading] = useState(true);

  const [connectorType, setConnectorType] = useState("");
  const [name, setName] = useState("");

  const [formSchema, setFormSchema] = useState<ConnectionFormSchema | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);

  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);

  const [saving, setSaving] = useState(false);
  const [saveAnyway, setSaveAnyway] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setConnectorsLoading(true);
      try {
        const list = await getConnectors();
        if (!cancelled) setConnectors(list);
      } catch (err) {
        if (!cancelled) {
          showError(
            err instanceof Error ? err.message : "Failed to load engine types",
          );
        }
      } finally {
        if (!cancelled) setConnectorsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showError]);

  const selectedConnector = useMemo(
    () => connectors.find((c) => c.connector_type === connectorType),
    [connectors, connectorType],
  );

  const loadFormSchema = useCallback(async (type: string) => {
    setSchemaLoading(true);
    setFormSchema(null);
    setConfig({});
    setFieldErrors({});
    setTestResult(null);
    setSaveAnyway(false);
    try {
      const schema = await getConnectionFormSchema(type);
      setFormSchema(schema);
      setConfig(applySchemaDefaults(schema, {}));
    } catch (err) {
      showError(
        err instanceof Error ? err.message : "Failed to load connection form schema",
      );
    } finally {
      setSchemaLoading(false);
    }
  }, [showError]);

  const handleSelectEngine = (type: string) => {
    setConnectorType(type);
    void loadFormSchema(type);
    setStep(1);
  };

  const validateForm = (): boolean => {
    if (!formSchema) return false;
    const errors = validateConnectionConfig(formSchema, config);
    setFieldErrors(errors);
    return !hasValidationErrors(errors);
  };

  const handleTest = async () => {
    if (!formSchema || !connectorType || !validateForm()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testConnection({
        connector_type: connectorType,
        connection_config: applySchemaDefaults(formSchema, config),
      });
      setTestResult(result);
      const message =
        result.success && result.latency_ms != null
          ? `${result.message} (${result.latency_ms.toFixed(0)} ms)`
          : result.message;
      if (result.success) {
        showSuccess(message);
      } else {
        showError(message);
      }
      setStep(2);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Connection test failed");
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async (force = false) => {
    if (!formSchema || !connectorType || !name.trim()) return;
    if (!force && !testResult?.success && !saveAnyway) return;
    if (!validateForm()) return;

    setSaving(true);
    try {
      const ds = await createDataSource({
        name: name.trim(),
        connector_type: connectorType,
        connection_config: applySchemaDefaults(formSchema, config),
        is_active: true,
      });
      navigate(`/admin/data-sources/${ds.id}/schema/import`);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to save data source");
    } finally {
      setSaving(false);
    }
  };

  const canProceedToConnection = Boolean(connectorType);
  const canTest = canProceedToConnection && formSchema && !schemaLoading;
  const canSave = name.trim().length > 0 && (testResult?.success || saveAnyway);

  return (
    <div className="page">
      <PageHeader
        title="Add Data Source"
        description="Connect a database by choosing an engine and filling in the adapter-provided form."
        actions={
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => navigate("/admin")}
          >
            Cancel
          </button>
        }
      />

      <ol className="wizard-steps">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={`wizard-steps__item${i === step ? " wizard-steps__item--active" : ""}${i < step ? " wizard-steps__item--done" : ""}`}
          >
            <span className="wizard-steps__num">{i + 1}</span>
            {label}
          </li>
        ))}
      </ol>

      {step === 0 && (
        <section className="wizard-panel">
          <h2 className="wizard-panel__title">Choose SQL engine</h2>
          {connectorsLoading && (
            <LoadingState message="Loading available engines…" />
          )}
          {!connectorsLoading && (
            <div className="engine-grid">
              {connectors.map((c) => (
                <button
                  key={c.connector_type}
                  type="button"
                  className={`engine-card${connectorType === c.connector_type ? " engine-card--selected" : ""}`}
                  onClick={() => handleSelectEngine(c.connector_type)}
                >
                  <span className="engine-card__name">
                    {formatConnectorLabel(c.connector_type, c.display_name)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {step >= 1 && step < 2 && (
        <section className="wizard-panel">
          <h2 className="wizard-panel__title">Connection details</h2>
          <p className="wizard-panel__subtitle">
            Engine:{" "}
            <strong>
              {formatConnectorLabel(
                connectorType,
                selectedConnector?.display_name ?? connectorType,
              )}
            </strong>
          </p>

          <label className="form-field">
            <span className="form-field__label">Display name</span>
            <input
              className="form-field__input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Production Warehouse"
            />
          </label>

          {schemaLoading && (
            <LoadingState message="Loading connection form schema…" />
          )}
          {formSchema && !schemaLoading && (
            <ConnectionForm
              schema={formSchema}
              values={config}
              onChange={setConfig}
              errors={fieldErrors}
              disabled={testing || saving}
            />
          )}

          {testing && (
            <LoadingState message="Testing connection — this may take a moment…" />
          )}

          <div className="wizard-actions">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setStep(0)}
              disabled={testing}
            >
              Back
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={!canTest || testing}
              onClick={() => void handleTest()}
            >
              {testing ? "Testing connection…" : "Test connection"}
            </button>
          </div>
        </section>
      )}

      {step >= 2 && testResult && (
        <section className="wizard-panel">
          <h2 className="wizard-panel__title">Save data source</h2>
          {!testResult.success && (
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={saveAnyway}
                onChange={(e) => setSaveAnyway(e.target.checked)}
              />
              Save anyway — I will fix the connection later
            </label>
          )}
          <div className="wizard-actions">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setStep(1)}
              disabled={saving}
            >
              Back
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={!canSave || saving}
              onClick={() => void handleSave(false)}
            >
              {saving ? "Saving…" : "Save data source"}
            </button>
            {testResult.success && (
              <button
                type="button"
                className="btn btn--secondary"
                disabled={saving}
                onClick={() => void handleSave(true)}
              >
                Save & import schema
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
