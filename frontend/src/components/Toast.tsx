import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface Toast {
  id: number;
  message: string;
  kind: "success" | "error";
}

const ToastContext = createContext<(message: string, kind?: "success" | "error") => void>(
  () => {},
);

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, kind: "success" | "error" = "success") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, kind }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div style={{ position: "fixed", bottom: 20, right: 20, display: "grid", gap: 8, zIndex: 50 }}>
        {toasts.map((t) => (
          <div
            key={t.id}
            style={{
              background: t.kind === "error" ? "#fee2e2" : "#dcfce7",
              color: t.kind === "error" ? "#b91c1c" : "#15803d",
              border: `1px solid ${t.kind === "error" ? "#fecaca" : "#bbf7d0"}`,
              padding: "10px 14px",
              borderRadius: 8,
              fontSize: 14,
              boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
