import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  completeSetup,
  getOllamaRecommendation,
  getSetupStatus,
} from "@/api/client";
import type { OllamaModelRecommendation } from "@/types/contracts";

const STEPS = ["Welcome", "LLM", "Ollama", "Done"] as const;

type LlmChoice = "ollama" | "later";

export default function SetupWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [llmChoice, setLlmChoice] = useState<LlmChoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progressLog, setProgressLog] = useState<string[]>([]);

  const isDesktop = Boolean(window.desktopApp?.getSystemSpecs);
  const [totalRamGb, setTotalRamGb] = useState(8);
  const [recommendation, setRecommendation] = useState<OllamaModelRecommendation | null>(null);
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("http://127.0.0.1:11434");

  const visibleSteps = useMemo(() => {
    if (llmChoice === "ollama") {
      return STEPS;
    }
    return STEPS.filter((name) => name !== "Ollama");
  }, [llmChoice]);

  const currentStepName = visibleSteps[step] ?? "Done";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await getSetupStatus();
        if (status.complete || !status.wizard_required) {
          navigate("/", { replace: true });
          return;
        }
        setOllamaBaseUrl(status.default_ollama_base_url);
      } catch {
        // Allow wizard to proceed if status check fails.
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  useEffect(() => {
    if (!isDesktop || !window.desktopApp?.getSystemSpecs) {
      return;
    }
    let cancelled = false;
    (async () => {
      const specs = await window.desktopApp!.getSystemSpecs!();
      if (cancelled) {
        return;
      }
      setTotalRamGb(specs.totalRamGb);
      const rec = window.desktopApp?.recommendOllamaModel
        ? await window.desktopApp.recommendOllamaModel(specs.totalRamGb)
        : await getOllamaRecommendation(specs.totalRamGb);
      if (!cancelled) {
        setRecommendation(rec);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isDesktop]);

  useEffect(() => {
    if (isDesktop || llmChoice !== "ollama") {
      return;
    }
    let cancelled = false;
    (async () => {
      const rec = await getOllamaRecommendation(totalRamGb);
      if (!cancelled) {
        setRecommendation(rec);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isDesktop, llmChoice, totalRamGb]);

  const appendProgress = useCallback((message: string) => {
    setProgressLog((current) => [...current.slice(-20), message]);
  }, []);

  const runOllamaSetup = useCallback(async () => {
    if (!recommendation) {
      throw new Error("No model recommendation available.");
    }

    const baseUrl = ollamaBaseUrl;
    const desktop = window.desktopApp;

    if (desktop?.onOllamaProgress) {
      const unsubscribe = desktop.onOllamaProgress((progress) => {
        appendProgress(progress.message);
      });
      try {
        let status = desktop.getOllamaStatus
          ? await desktop.getOllamaStatus(baseUrl)
          : { installed: false, running: false, baseUrl };

        if (!status.installed) {
          appendProgress("Installing Ollama…");
          if (desktop.installOllama) {
            await desktop.installOllama();
          } else {
            throw new Error("Automatic Ollama install is only available in the desktop app.");
          }
        }

        appendProgress("Starting Ollama…");
        if (desktop.startOllama) {
          status = await desktop.startOllama(baseUrl);
        }
        if (!status.running) {
          throw new Error("Ollama did not start. Try opening the Ollama app manually.");
        }

        appendProgress(`Downloading ${recommendation.label}…`);
        if (desktop.pullOllamaModel) {
          await desktop.pullOllamaModel(recommendation.model);
        }
      } finally {
        unsubscribe();
      }
    } else {
      appendProgress(
        "Configure Ollama on this server, then pull the recommended model manually.",
      );
    }

    await completeSetup({
      ollama_self_host: true,
      provider: "ollama",
      ollama_base_url: baseUrl,
      ollama_model: recommendation.model,
    });
  }, [appendProgress, ollamaBaseUrl, recommendation]);

  const finishLater = useCallback(async () => {
    await completeSetup({ ollama_self_host: false });
  }, []);

  const handleNext = async () => {
    setError(null);

    if (currentStepName === "Welcome") {
      setStep((current) => current + 1);
      return;
    }

    if (currentStepName === "LLM") {
      if (!llmChoice) {
        setError("Choose how you want to run the language model.");
        return;
      }
      if (llmChoice === "later") {
        setBusy(true);
        try {
          await finishLater();
          setStep(visibleSteps.length - 1);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to save setup choice.");
        } finally {
          setBusy(false);
        }
        return;
      }
      setStep((current) => current + 1);
      return;
    }

    if (currentStepName === "Ollama") {
      setBusy(true);
      setProgressLog([]);
      try {
        await runOllamaSetup();
        setStep((current) => current + 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ollama setup failed.");
      } finally {
        setBusy(false);
      }
      return;
    }

    navigate("/", { replace: true });
  };

  if (loading) {
    return (
      <div className="setup-wizard">
        <p className="setup-wizard__loading">Preparing setup…</p>
      </div>
    );
  }

  return (
    <div className="setup-wizard">
      <div className="setup-wizard__card card">
        <header className="setup-wizard__header">
          <h1 className="setup-wizard__title">Welcome to Queryline</h1>
          <p className="setup-wizard__subtitle">
            A quick setup to get you running. You can change these choices later in Admin settings.
          </p>
        </header>

        <ol className="wizard-steps">
          {visibleSteps.map((name, index) => (
            <li
              key={name}
              className={`wizard-steps__item${index === step ? " wizard-steps__item--active" : ""}${index < step ? " wizard-steps__item--done" : ""}`}
            >
              <span className="wizard-steps__num">{index + 1}</span>
              {name}
            </li>
          ))}
        </ol>

        {currentStepName === "Welcome" && (
          <section className="wizard-panel">
            <h2 className="wizard-panel__title">Your machine, your workspace</h2>
            <p className="wizard-panel__subtitle">
              This app runs on your computer. The signed-in OS user becomes the default
              administrator and cannot be demoted later.
            </p>
            <ul className="setup-wizard__list">
              <li>Connect databases and ask questions in plain English</li>
              <li>Choose a local Ollama model or configure a cloud provider later</li>
              <li>Invite other users and assign roles from Admin</li>
            </ul>
          </section>
        )}

        {currentStepName === "LLM" && (
          <section className="wizard-panel">
            <h2 className="wizard-panel__title">How should we run the language model?</h2>
            <p className="wizard-panel__subtitle">
              Self-hosting with Ollama keeps data on your machine. You can skip this and pick
              Anthropic, Gemini, or Ollama later under Admin → LLM settings.
            </p>
            <div className="setup-wizard__choices">
              <button
                type="button"
                className={`setup-choice${llmChoice === "ollama" ? " setup-choice--selected" : ""}`}
                onClick={() => setLlmChoice("ollama")}
              >
                <strong>Self-host with Ollama</strong>
                <span>Install and download a model sized for this computer.</span>
              </button>
              <button
                type="button"
                className={`setup-choice${llmChoice === "later" ? " setup-choice--selected" : ""}`}
                onClick={() => setLlmChoice("later")}
              >
                <strong>Decide later</strong>
                <span>Skip for now and configure a provider in Admin settings.</span>
              </button>
            </div>
          </section>
        )}

        {currentStepName === "Ollama" && (
          <section className="wizard-panel">
            <h2 className="wizard-panel__title">Set up Ollama</h2>
            <p className="wizard-panel__subtitle">
              {isDesktop
                ? "We will install Ollama if needed, start it, and download a model matched to your hardware."
                : "Use the Ollama sidecar or an existing Ollama server on this host."}
            </p>
            {recommendation && (
              <div className="setup-wizard__recommendation">
                <p>
                  <strong>Recommended model:</strong> {recommendation.label} (
                  <code>{recommendation.model}</code>)
                </p>
                <p className="setup-wizard__reason">{recommendation.reason}</p>
                <p className="setup-wizard__specs">Detected memory: ~{totalRamGb} GB</p>
              </div>
            )}
            {progressLog.length > 0 && (
              <pre className="setup-wizard__progress" aria-live="polite">
                {progressLog.join("\n")}
              </pre>
            )}
          </section>
        )}

        {currentStepName === "Done" && (
          <section className="wizard-panel">
            <h2 className="wizard-panel__title">You&apos;re all set</h2>
            <p className="wizard-panel__subtitle">
              Sign in with your system account to start. Administrators can add data sources and
              adjust LLM settings anytime.
            </p>
          </section>
        )}

        {error && <p className="form-field__error setup-wizard__error">{error}</p>}

        <div className="wizard-actions">
          {step > 0 && currentStepName !== "Done" && (
            <button
              type="button"
              className="btn btn--secondary"
              disabled={busy}
              onClick={() => setStep((current) => Math.max(0, current - 1))}
            >
              Back
            </button>
          )}
          <button
            type="button"
            className="btn btn--primary"
            disabled={busy}
            onClick={() => void handleNext()}
          >
            {busy
              ? "Working…"
              : currentStepName === "Done"
                ? "Continue to sign in"
                : currentStepName === "Ollama"
                  ? "Install and continue"
                  : currentStepName === "LLM" && llmChoice === "later"
                    ? "Skip for now"
                    : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
