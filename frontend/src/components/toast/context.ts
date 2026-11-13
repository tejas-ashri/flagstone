import { createContext, useContext } from "react";

export interface ToastOptions {
  kind?: "info" | "success" | "error";
  // Adds an action button, e.g. Undo. The toast closes when it is clicked.
  action?: { label: string; onClick: () => void };
}

export type ShowToast = (message: string, options?: ToastOptions) => void;

export const ToastContext = createContext<ShowToast | null>(null);

export function useToast(): ShowToast {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
