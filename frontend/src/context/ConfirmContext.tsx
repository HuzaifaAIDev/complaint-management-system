import React, { createContext, useCallback, useContext, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";

interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | undefined>(undefined);

/**
 * This dialog only gates the user's own follow-through on an action they
 * already chose in the UI. It is not, and must never be treated as, a
 * security boundary - the backend independently authorizes and validates
 * every request regardless of whether this dialog was shown.
 */
export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<(value: boolean) => void>();

  const confirm = useCallback<ConfirmFn>((opts) => {
    setOptions(opts);
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  const handle = (result: boolean) => {
    setOptions(null);
    resolver.current?.(result);
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {options && (
        <div className="modal-overlay" role="presentation" onClick={() => handle(false)}>
          <div
            className="modal-card"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-desc"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`modal-icon${options.danger ? " modal-icon-danger" : ""}`}>
              <AlertTriangle size={18} />
            </div>
            <h2 id="confirm-dialog-title">{options.title}</h2>
            {options.description && <p id="confirm-dialog-desc" className="modal-desc">{options.description}</p>}
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => handle(false)} autoFocus>
                {options.cancelLabel || "Cancel"}
              </button>
              <button
                className={options.danger ? "btn-danger" : "btn-primary"}
                onClick={() => handle(true)}
              >
                {options.confirmLabel || "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within ConfirmProvider");
  return ctx;
}
