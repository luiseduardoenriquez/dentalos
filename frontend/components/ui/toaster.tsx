"use client";

import { useEffect } from "react";
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { useToastStore, type Toast, type ToastType } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Icon Map ─────────────────────────────────────────────────────────────────

const TOAST_ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 className="h-5 w-5 text-success-600 shrink-0" />,
  error: <AlertCircle className="h-5 w-5 text-destructive-600 shrink-0" />,
  warning: <AlertTriangle className="h-5 w-5 text-accent-600 shrink-0" />,
  info: <Info className="h-5 w-5 text-primary-600 shrink-0" />,
};

// ─── Style Map ────────────────────────────────────────────────────────────────

const TOAST_STYLES: Record<ToastType, string> = {
  success:
    "border-success-500/30 bg-success-50 dark:bg-success-700/20 dark:border-success-500/40",
  error:
    "border-destructive-500/30 bg-destructive-50 dark:bg-destructive-700/20 dark:border-destructive-500/40",
  warning:
    "border-accent-500/30 bg-accent-50 dark:bg-accent-700/20 dark:border-accent-500/40",
  info: "border-primary-500/30 bg-primary-50 dark:bg-primary-700/20 dark:border-primary-500/40",
};

// ─── Toast Item Component ─────────────────────────────────────────────────────

interface ToastItemProps {
  toast: Toast;
  onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        "flex items-start gap-3 w-full max-w-sm rounded-lg border p-4 shadow-lg",
        "animate-in slide-in-from-right-full duration-300",
        "bg-white dark:bg-zinc-900",
        TOAST_STYLES[toast.type],
      )}
    >
      {/* Icon */}
      <div className="mt-0.5">{TOAST_ICONS[toast.type]}</div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-foreground leading-snug">{toast.title}</p>
        {toast.description && (
          <p className="mt-1 text-sm text-muted-foreground leading-snug">{toast.description}</p>
        )}
      </div>

      {/* Dismiss button */}
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Cerrar notificación"
        className={cn(
          "shrink-0 rounded-md p-1 transition-colors",
          "text-muted-foreground hover:text-foreground hover:bg-black/5 dark:hover:bg-white/5",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring",
        )}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ─── Toaster Container ────────────────────────────────────────────────────────

/**
 * Global toast notification container.
 *
 * Renders in the bottom-right corner on desktop (bottom-center on mobile).
 * Reads from the global toast store (useToastStore) — does not need any props.
 *
 * Mount this once at the root layout level via Providers.
 */
export function Toaster() {
  const { toasts, dismiss } = useToastStore();

  // Remove any lingering toasts on unmount (route navigation)
  useEffect(() => {
    return () => {
      // Intentionally do NOT clear toasts on navigation — cross-page notifications
      // are common after form submissions that redirect.
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-label="Notificaciones"
      className={cn(
        "fixed z-50 flex flex-col gap-2",
        // Mobile: bottom center, full width with padding
        "bottom-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-sm",
        // Tablet+: bottom right corner
        "sm:left-auto sm:right-4 sm:translate-x-0 sm:w-auto",
      )}
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
      ))}
    </div>
  );
}
