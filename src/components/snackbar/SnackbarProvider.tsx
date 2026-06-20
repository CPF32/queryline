import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type SnackbarVariant = "success" | "error" | "info";

export interface SnackbarOptions {
  message: string;
  variant?: SnackbarVariant;
  durationMs?: number;
}

interface SnackbarItem {
  id: string;
  message: string;
  variant: SnackbarVariant;
}

interface SnackbarContextValue {
  show: (options: SnackbarOptions) => void;
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
  showInfo: (message: string) => void;
}

const SnackbarContext = createContext<SnackbarContextValue | null>(null);

const DEFAULT_DURATION_MS: Record<SnackbarVariant, number> = {
  success: 4000,
  error: 6000,
  info: 5000,
};

function variantLabel(variant: SnackbarVariant): string {
  if (variant === "success") return "Success";
  if (variant === "error") return "Error";
  return "Notice";
}

export function SnackbarProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<SnackbarItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const show = useCallback(
    ({ message, variant = "info", durationMs }: SnackbarOptions) => {
      const trimmed = message.trim();
      if (!trimmed) {
        return;
      }

      const id = crypto.randomUUID();
      const resolvedVariant = variant;
      setItems((current) => [...current.slice(-2), { id, message: trimmed, variant: resolvedVariant }]);

      window.setTimeout(
        () => dismiss(id),
        durationMs ?? DEFAULT_DURATION_MS[resolvedVariant],
      );
    },
    [dismiss],
  );

  const value = useMemo(
    () => ({
      show,
      showSuccess: (message: string) => show({ message, variant: "success" }),
      showError: (message: string) => show({ message, variant: "error" }),
      showInfo: (message: string) => show({ message, variant: "info" }),
    }),
    [show],
  );

  return (
    <SnackbarContext.Provider value={value}>
      {children}
      <div className="snackbar-host" aria-live="polite" aria-relevant="additions">
        {items.map((item) => (
          <div
            key={item.id}
            className={`snackbar snackbar--${item.variant}`}
            role="status"
          >
            <span className="snackbar__label">{variantLabel(item.variant)}</span>
            <p className="snackbar__message">{item.message}</p>
            <button
              type="button"
              className="snackbar__dismiss"
              onClick={() => dismiss(item.id)}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </SnackbarContext.Provider>
  );
}

export function useSnackbar(): SnackbarContextValue {
  const context = useContext(SnackbarContext);
  if (!context) {
    throw new Error("useSnackbar must be used within SnackbarProvider");
  }
  return context;
}
