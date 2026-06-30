import { useAppUpdate } from "@/updates/AppUpdateContext";

export default function UpdateBanner() {
  const {
    status,
    currentVersion,
    dismissedVersion,
    dismissedError,
    dismissAvailable,
    dismissError,
    downloadUpdate,
    installUpdate,
  } = useAppUpdate();

  const availableVersion = status.version;
  const showAvailableBanner =
    (status.phase === "available" || status.phase === "downloading" || status.phase === "ready") &&
    availableVersion &&
    dismissedVersion !== availableVersion;

  const showErrorBanner =
    status.phase === "error" &&
    !dismissedError &&
    (status.source === "manual" || Boolean(status.manualDownloadUrl));

  if (!showAvailableBanner && !showErrorBanner) {
    return null;
  }

  if (showErrorBanner) {
    return (
      <div className="update-banner update-banner--error" role="alert">
        <div className="update-banner__content">
          <strong className="update-banner__title">Update check failed</strong>
          <span className="update-banner__message">
            {status.message ?? "Could not check for updates."}
          </span>
        </div>
        <div className="update-banner__actions">
          {status.manualDownloadUrl && (
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => void downloadUpdate()}
            >
              Open releases
            </button>
          )}
          <button type="button" className="btn btn--ghost btn--sm" onClick={dismissError}>
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  const progressLabel =
    status.phase === "downloading" && typeof status.percent === "number"
      ? `Downloading… ${Math.round(status.percent)}%`
      : status.phase === "ready"
        ? "Update downloaded — restart to apply"
        : `Version ${availableVersion} is available${currentVersion ? ` (you have ${currentVersion})` : ""}`;

  const handleUpdate = async () => {
    if (status.phase === "ready") {
      await installUpdate();
      return;
    }
    await downloadUpdate();
  };

  return (
    <div className="update-banner" role="status" aria-live="polite">
      <div className="update-banner__content">
        <strong className="update-banner__title">Update available</strong>
        <span className="update-banner__message">{progressLabel}</span>
      </div>
      <div className="update-banner__actions">
        {status.phase !== "downloading" && status.phase !== "ready" && (
          <button type="button" className="btn btn--ghost btn--sm" onClick={dismissAvailable}>
            Later
          </button>
        )}
        <button
          type="button"
          className="btn btn--primary btn--sm"
          disabled={status.phase === "downloading"}
          onClick={() => void handleUpdate()}
        >
          {status.phase === "ready"
            ? "Restart and update"
            : status.phase === "downloading"
              ? "Downloading…"
              : status.fallback
                ? "Download from GitHub"
                : "Update"}
        </button>
      </div>
    </div>
  );
}
