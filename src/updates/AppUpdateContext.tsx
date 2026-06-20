import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type UpdatePhase =
  | "idle"
  | "checking"
  | "available"
  | "downloading"
  | "ready"
  | "up-to-date"
  | "error";

export interface AppUpdateStatus {
  phase: UpdatePhase;
  version?: string;
  currentVersion?: string;
  percent?: number;
  message?: string;
  releaseNotes?: string | null;
  source?: string;
}

interface AppUpdateContextValue {
  status: AppUpdateStatus;
  currentVersion: string | null;
  isDesktop: boolean;
  dismissedVersion: string | null;
  dismissedError: boolean;
  dismissAvailable: () => void;
  dismissError: () => void;
  checkForUpdates: (manual?: boolean) => Promise<void>;
  downloadUpdate: () => Promise<void>;
  installUpdate: () => Promise<void>;
}

const AppUpdateContext = createContext<AppUpdateContextValue | null>(null);

function normalizeStatus(raw: Record<string, unknown>): AppUpdateStatus {
  return {
    phase: (raw.phase as UpdatePhase) ?? "idle",
    version: typeof raw.version === "string" ? raw.version : undefined,
    currentVersion: typeof raw.currentVersion === "string" ? raw.currentVersion : undefined,
    percent: typeof raw.percent === "number" ? raw.percent : undefined,
    message: typeof raw.message === "string" ? raw.message : undefined,
    releaseNotes: typeof raw.releaseNotes === "string" ? raw.releaseNotes : null,
    source: typeof raw.source === "string" ? raw.source : undefined,
  };
}

export function AppUpdateProvider({ children }: { children: ReactNode }) {
  const desktop = window.desktopApp;
  const isDesktop = Boolean(desktop?.onAppUpdateStatus);
  const [status, setStatus] = useState<AppUpdateStatus>({ phase: "idle" });
  const [currentVersion, setCurrentVersion] = useState<string | null>(null);
  const [dismissedVersion, setDismissedVersion] = useState<string | null>(null);
  const [dismissedError, setDismissedError] = useState(false);

  useEffect(() => {
    if (!desktop?.onAppUpdateStatus) {
      return;
    }

    void desktop.getAppVersion?.().then((version) => {
      setCurrentVersion(version);
    });

    void desktop.getAppUpdateStatus?.().then((raw) => {
      if (raw && typeof raw === "object") {
        setStatus(normalizeStatus(raw as Record<string, unknown>));
      }
    });

    const unsubscribe = desktop.onAppUpdateStatus((next) => {
      const normalized = normalizeStatus(next as Record<string, unknown>);
      setStatus(normalized);
      if (normalized.phase === "error") {
        setDismissedError(false);
      }
      if (normalized.phase === "available" && normalized.version) {
        setDismissedVersion((current) =>
          current === normalized.version ? current : null,
        );
      }
    });

    void desktop.checkForAppUpdate?.(false);

    return unsubscribe;
  }, [desktop]);

  const checkForUpdates = useCallback(
    async (manual = true) => {
      if (!desktop?.checkForAppUpdate) {
        setStatus({
          phase: "error",
          source: "manual",
          message: "Updates are only available in the installed desktop app.",
        });
        setDismissedError(false);
        return;
      }

      setDismissedError(false);
      await desktop.checkForAppUpdate(manual);
    },
    [desktop],
  );

  const downloadUpdate = useCallback(async () => {
    await desktop?.downloadAppUpdate?.();
  }, [desktop]);

  const installUpdate = useCallback(async () => {
    await desktop?.installAppUpdate?.();
  }, [desktop]);

  const dismissAvailable = useCallback(() => {
    if (status.version) {
      setDismissedVersion(status.version);
    }
  }, [status.version]);

  const dismissError = useCallback(() => {
    setDismissedError(true);
  }, []);

  const value = useMemo(
    () => ({
      status,
      currentVersion,
      isDesktop,
      dismissedVersion,
      dismissedError,
      dismissAvailable,
      dismissError,
      checkForUpdates,
      downloadUpdate,
      installUpdate,
    }),
    [
      status,
      currentVersion,
      isDesktop,
      dismissedVersion,
      dismissedError,
      dismissAvailable,
      dismissError,
      checkForUpdates,
      downloadUpdate,
      installUpdate,
    ],
  );

  return <AppUpdateContext.Provider value={value}>{children}</AppUpdateContext.Provider>;
}

export function useAppUpdate() {
  const context = useContext(AppUpdateContext);
  if (!context) {
    throw new Error("useAppUpdate must be used within AppUpdateProvider");
  }
  return context;
}
