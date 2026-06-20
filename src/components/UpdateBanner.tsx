import { useEffect, useState } from "react";

type UpdatePhase =
  | "idle"
  | "checking"
  | "available"
  | "downloading"
  | "ready"
  | "error";

interface UpdateStatus {
  phase: UpdatePhase;
  version?: string;
  percent?: number;
  message?: string;
}

export default function UpdateBanner() {
  const [status, setStatus] = useState<UpdateStatus>({ phase: "idle" });
  const [dismissedVersion, setDismissedVersion] = useState<string | null>(null);
  const [currentVersion, setCurrentVersion] = useState<string | null>(null);

  useEffect(() => {
    const desktop = window.desktopApp;
    if (!desktop?.onAppUpdateStatus) {
      return;
    }

    void desktop.getAppVersion?.().then((version) => {
      setCurrentVersion(version);
    });

    return desktop.onAppUpdateStatus((next) => {
      setStatus({
        phase: next.phase as UpdatePhase,
        version: next.version,
        percent: next.percent,
        message: next.message,
      });
    });
  }, []);

  if (!window.desktopApp?.onAppUpdateStatus) {
    return null;
  }

  const availableVersion = status.version;
  const showBanner =
    (status.phase === "available" || status.phase === "downloading" || status.phase === "ready") &&
    availableVersion &&
    dismissedVersion !== availableVersion;

  if (!showBanner) {
    return null;
  }

  const handleLater = () => {
    if (availableVersion) {
      setDismissedVersion(availableVersion);
    }
  };

  const handleUpdate = async () => {
    const desktop = window.desktopApp;
    if (!desktop) {
      return;
    }

    if (status.phase === "ready") {
      await desktop.installAppUpdate?.();
      return;
    }

    await desktop.downloadAppUpdate?.();
  };

  const progressLabel =
    status.phase === "downloading" && typeof status.percent === "number"
      ? `Downloading… ${Math.round(status.percent)}%`
      : status.phase === "ready"
        ? "Update downloaded — restart to apply"
        : `Version ${availableVersion} is available${currentVersion ? ` (you have ${currentVersion})` : ""}`;

  return (
    <div className="update-banner" role="status" aria-live="polite">
      <div className="update-banner__content">
        <strong className="update-banner__title">Update available</strong>
        <span className="update-banner__message">{progressLabel}</span>
      </div>
      <div className="update-banner__actions">
        {status.phase !== "downloading" && status.phase !== "ready" && (
          <button type="button" className="btn btn--ghost btn--sm" onClick={handleLater}>
            Later
          </button>
        )}
        <button
          type="button"
          className="btn btn--primary btn--sm"
          disabled={status.phase === "downloading"}
          onClick={() => void handleUpdate()}
        >
          {status.phase === "ready" ? "Restart and update" : "Update"}
        </button>
      </div>
    </div>
  );
}
