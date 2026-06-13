import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (message: string, type?: ToastType) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast container — fixed bottom-right */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((toast) => {
          const styles: Record<ToastType, string> = {
            success: 'bg-green-600 text-white',
            error: 'bg-red-600 text-white',
            warning: 'bg-amber-500 text-white',
            info: 'bg-gray-800 text-white',
          };
          const icons: Record<ToastType, string> = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
          };
          return (
            <div
              key={toast.id}
              className={`px-4 py-3 rounded-lg shadow-lg text-sm flex items-center gap-2 animate-slide-up ${styles[toast.type]}`}
            >
              <span className="font-bold text-base">{icons[toast.type]}</span>
              <span className="flex-1">{toast.message}</span>
              <button
                onClick={() => removeToast(toast.id)}
                className="opacity-70 hover:opacity-100 ml-2 text-lg leading-none"
              >
                ×
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
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
