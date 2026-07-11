// Minimal toast context. API errors from TanStack Query are routed here via a
// module-level bridge so the QueryClient (created outside React) can raise
// toasts without prop drilling.

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

type ToastKind = 'error' | 'success';

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
  action?: ToastAction;
}

interface ToastContextValue {
  notify: (message: string, kind?: ToastKind, action?: ToastAction) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let bridge: ((message: string, kind: ToastKind) => void) | null = null;

/** Used by the QueryClient error handlers outside the React tree. */
export function notifyFromOutside(message: string, kind: ToastKind = 'error'): void {
  bridge?.(message, kind);
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used inside ToastProvider');
  return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const notify = useCallback((message: string, kind: ToastKind = 'success', action?: ToastAction) => {
    const id = nextId.current++;
    setToasts((current) => [...current, { id, kind, message, action }]);
    // Toasts with an action (e.g. Undo) stay longer so users can react.
    setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), action ? 8000 : 5000);
  }, []);

  useEffect(() => {
    bridge = (message, kind) => notify(message, kind);
    return () => {
      bridge = null;
    };
  }, [notify]);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-50 flex w-80 flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-start justify-between gap-2 rounded-lg px-4 py-3 text-sm shadow-lg ${
              toast.kind === 'error' ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
            }`}
          >
            <span className="flex-1">{toast.message}</span>
            {toast.action && (
              <button
                type="button"
                className="shrink-0 rounded bg-white/20 px-2 py-0.5 font-semibold hover:bg-white/30"
                onClick={() => {
                  toast.action?.onClick();
                  setToasts((current) => current.filter((item) => item.id !== toast.id));
                }}
              >
                {toast.action.label}
              </button>
            )}
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
