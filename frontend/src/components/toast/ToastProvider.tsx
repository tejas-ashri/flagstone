import { useCallback, useState, type ReactNode } from "react";
import { ToastContext, type ToastOptions } from "./context";

interface Toast extends ToastOptions {
  id: number;
  message: string;
}

const DURATION_MS = 5000;
let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => setToasts(ts => ts.filter(t => t.id !== id)), []);

  const show = useCallback(
    (message: string, options: ToastOptions = {}) => {
      const id = nextId++;
      setToasts(ts => [...ts.slice(-3), { id, message, ...options }]);
      setTimeout(() => dismiss(id), options.kind === "error" ? DURATION_MS * 2 : DURATION_MS);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.kind ?? "info"}`} role={t.kind === "error" ? "alert" : "status"}>
            <span>{t.message}</span>
            {t.action && (
              <button
                type="button"
                className="btn small"
                onClick={() => {
                  t.action!.onClick();
                  dismiss(t.id);
                }}
              >
                {t.action.label}
              </button>
            )}
            <button type="button" className="toast-close" aria-label="Dismiss" onClick={() => dismiss(t.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
