import { useCallback, useEffect, useRef, useState } from "react";
import {
  getLlmSettings,
  testLlmSettings,
  updateLlmSettings,
} from "@/api/client";
import PageHeader, { ErrorState, LoadingState } from "@/admin/AdminUi";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import type { LlmProvider, LlmSettings } from "@/types/contracts";

const AUTO_SAVE_MS = 700;

const PROVIDERS: { id: LlmProvider; label: string; description: string }[] = [
  {
    id: "anthropic",
    label: "Anthropic (Claude)",
    description: "Cloud API with an API key.",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    description: "Cloud API with an API key.",
  },
  {
    id: "ollama",
    label: "Ollama (local)",
    description: "Run models on this machine — no API key required.",
  },
];

type SaveStatus = "idle" | "saving" | "saved" | "error";

export default function LlmSettingsPage() {
  const { showSuccess, showError } = useSnackbar();
  const [settings, setSettings] = useState<LlmSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [provider, setProvider] = useState<LlmProvider>("anthropic");
  const [anthropicApiKey, setAnthropicApiKey] = useState("");
  const [anthropicModel, setAnthropicModel] = useState("");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("");
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("http://127.0.0.1:11434");
  const [ollamaModel, setOllamaModel] = useState("llama3.1");

  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [testing, setTesting] = useState(false);

  const autoSaveEnabledRef = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    autoSaveEnabledRef.current = false;
    try {
      const data = await getLlmSettings();
      setSettings(data);
      setProvider(data.provider);
      setAnthropicModel(data.anthropic_model);
      setGeminiModel(data.gemini_model);
      setOllamaBaseUrl(data.ollama_base_url);
      setOllamaModel(data.ollama_model);
      setAnthropicApiKey("");
      setGeminiApiKey("");
      setSaveStatus("idle");
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load LLM settings");
    } finally {
      setLoading(false);
      window.setTimeout(() => {
        autoSaveEnabledRef.current = true;
      }, 0);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const buildPayload = useCallback(() => {
    const payload: Parameters<typeof updateLlmSettings>[0] = {
      provider,
      anthropic_model: anthropicModel,
      gemini_model: geminiModel,
      ollama_base_url: ollamaBaseUrl,
      ollama_model: ollamaModel,
    };
    if (anthropicApiKey) payload.anthropic_api_key = anthropicApiKey;
    if (geminiApiKey) payload.gemini_api_key = geminiApiKey;
    return payload;
  }, [
    provider,
    anthropicApiKey,
    anthropicModel,
    geminiApiKey,
    geminiModel,
    ollamaBaseUrl,
    ollamaModel,
  ]);

  const persist = useCallback(async () => {
    setSaveStatus("saving");
    try {
      const updated = await updateLlmSettings(buildPayload());
      setSettings(updated);
      setAnthropicApiKey("");
      setGeminiApiKey("");
      setSaveStatus("saved");
    } catch (err) {
      setSaveStatus("error");
      showError(err instanceof Error ? err.message : "Failed to save settings");
    }
  }, [buildPayload, showError]);

  useEffect(() => {
    if (!autoSaveEnabledRef.current) {
      return;
    }

    setSaveStatus((status) => (status === "saved" ? "idle" : status));

    const timer = window.setTimeout(() => {
      void persist();
    }, AUTO_SAVE_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [
    provider,
    anthropicApiKey,
    anthropicModel,
    geminiApiKey,
    geminiModel,
    ollamaBaseUrl,
    ollamaModel,
    persist,
  ]);

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await testLlmSettings(buildPayload());
      const message = result.latency_ms
        ? `${result.message} (${result.latency_ms} ms)`
        : result.message;
      if (result.success) {
        showSuccess(message);
      } else {
        showError(message);
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setTesting(false);
    }
  };

  const saveStatusLabel =
    saveStatus === "saving"
      ? "Saving…"
      : saveStatus === "saved"
        ? "Saved"
        : saveStatus === "error"
          ? "Save failed"
          : null;

  if (loading) {
    return (
      <div className="page">
        <PageHeader title="LLM Settings" description="Choose a cloud API key or a local Ollama endpoint." />
        <LoadingState message="Loading LLM settings…" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="page">
        <PageHeader title="LLM Settings" />
        <ErrorState message={loadError} onRetry={() => void load()} />
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title="LLM Settings"
        description="Changes save automatically."
        actions={
          <div className="btn-group">
            {saveStatusLabel && (
              <span
                className={`llm-settings-status${saveStatus === "error" ? " llm-settings-status--error" : ""}`}
                aria-live="polite"
              >
                {saveStatusLabel}
              </span>
            )}
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => void handleTest()}
              disabled={testing || saveStatus === "saving"}
            >
              {testing ? "Testing…" : "Test connection"}
            </button>
          </div>
        }
      />

      <section className="card">
        <h2 className="card__title">Provider</h2>
        <div className="provider-grid">
          {PROVIDERS.map((item) => (
            <label key={item.id} className="provider-card">
              <input
                type="radio"
                name="llm-provider"
                value={item.id}
                checked={provider === item.id}
                onChange={() => setProvider(item.id)}
              />
              <span className="provider-card__label">{item.label}</span>
              <span className="provider-card__description">{item.description}</span>
            </label>
          ))}
        </div>
        {settings && (
          <p className="form-field__hint">
            Status: {settings.configured ? "configured" : "not configured"} · env file:{" "}
            <code>{settings.env_file_path}</code>
          </p>
        )}
      </section>

      {provider === "anthropic" && (
        <section className="card">
          <h2 className="card__title">Anthropic</h2>
          <label className="form-field">
            <span className="form-field__label">API key</span>
            <input
              className="form-field__input"
              type="password"
              autoComplete="off"
              placeholder={
                settings?.anthropic_api_key_set ? "Saved — enter to replace" : "sk-ant-…"
              }
              value={anthropicApiKey}
              onChange={(e) => setAnthropicApiKey(e.target.value)}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Model</span>
            <input
              className="form-field__input"
              value={anthropicModel}
              onChange={(e) => setAnthropicModel(e.target.value)}
            />
          </label>
        </section>
      )}

      {provider === "gemini" && (
        <section className="card">
          <h2 className="card__title">Gemini</h2>
          <label className="form-field">
            <span className="form-field__label">API key</span>
            <input
              className="form-field__input"
              type="password"
              autoComplete="off"
              placeholder={
                settings?.gemini_api_key_set ? "Saved — enter to replace" : "AIza…"
              }
              value={geminiApiKey}
              onChange={(e) => setGeminiApiKey(e.target.value)}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Model</span>
            <input
              className="form-field__input"
              value={geminiModel}
              onChange={(e) => setGeminiModel(e.target.value)}
            />
          </label>
        </section>
      )}

      {provider === "ollama" && (
        <section className="card">
          <h2 className="card__title">Ollama (local)</h2>
          <p className="form-field__hint">
            Install Ollama from{" "}
            <a href="https://ollama.com" target="_blank" rel="noreferrer">
              ollama.com
            </a>
            , then run <code>ollama pull {ollamaModel || "llama3.1"}</code>. Ollama runs as a
            system service (default <code>http://127.0.0.1:11434</code>), not inside this project
            folder.
          </p>
          <label className="form-field">
            <span className="form-field__label">Base URL</span>
            <input
              className="form-field__input"
              value={ollamaBaseUrl}
              onChange={(e) => setOllamaBaseUrl(e.target.value)}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Model</span>
            <input
              className="form-field__input"
              value={ollamaModel}
              onChange={(e) => setOllamaModel(e.target.value)}
            />
          </label>
        </section>
      )}
    </div>
  );
}
