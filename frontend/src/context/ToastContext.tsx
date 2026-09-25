import React, { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Info, X, LucideIcon } from "lucide-react";

type ToastKind = "success" | "error" | "warning" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  show: (kind: ToastKind, message: string) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const ICONS: Record<ToastKind, LucideIcon> = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

let idCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const show = useCallback((kind: ToastKind, message: string) => {
    const id = ++idCounter;
    setToasts((t) => [...t, { id, kind, message }]);
    window.setTimeout(() => dismiss(id), 5000);
  }, [dismiss]);

  const value: ToastContextValue = {
    show,
    success: (m) => show("success", m),
    error: (m) => show("error", m),
    warning: (m) => show("warning", m),
    info: (m) => show("info", m),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => {
          const Icon = ICONS[t.kind];
          return (
            <div key={t.id} className={`toast toast-${t.kind}`}>
              <Icon size={16} />
              <span>{t.message}</span>
              <button className="toast-dismiss" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
