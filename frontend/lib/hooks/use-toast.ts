"use client";

import { create } from "zustand";

// ─── Types ─────────────────────────────────────────────────────────────────────

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  type: ToastType;
  /** Duration in milliseconds before auto-dismiss. 0 = persistent. */
  duration: number;
}

export type ToastInput = Omit<Toast, "id">;

// ─── Store ─────────────────────────────────────────────────────────────────────

interface ToastStore {
  toasts: Toast[];
  toast: (input: ToastInput) => string;
  dismiss: (id: string) => void;
  dismiss_all: () => void;
}

let toastCounter = 0;

function generateId(): string {
  return `toast-${++toastCounter}-${Date.now()}`;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],

  toast: (input: ToastInput) => {
    const id = generateId();
    const toast: Toast = {
      id,
      duration: 5000, // 5 second default
      ...input,
    };

    set((state) => ({
      toasts: [...state.toasts, toast],
    }));

    // Auto-dismiss after duration (unless duration is 0 = persistent)
    if (toast.duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      }, toast.duration);
    }

    return id;
  },

  dismiss: (id: string) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  dismiss_all: () => {
    set({ toasts: [] });
  },
}));

// ─── Convenience Hook ──────────────────────────────────────────────────────────

interface ToastHelpers {
  toasts: Toast[];
  toast: (input: ToastInput) => string;
  success: (title: string, description?: string, duration?: number) => string;
  error: (title: string, description?: string, duration?: number) => string;
  warning: (title: string, description?: string, duration?: number) => string;
  info: (title: string, description?: string, duration?: number) => string;
  dismiss: (id: string) => void;
  dismiss_all: () => void;
}

/**
 * Hook for displaying toast notifications.
 *
 * @example
 * const { success, error } = useToast();
 *
 * // On save
 * success("Paciente guardado", "Los cambios se guardaron correctamente.");
 *
 * // On error
 * error("Error al guardar", "Inténtalo de nuevo.");
 */
export function useToast(): ToastHelpers {
  const { toasts, toast, dismiss, dismiss_all } = useToastStore();

  return {
    toasts,
    toast,

    success: (title: string, description?: string, duration = 4000) =>
      toast({ type: "success", title, description, duration }),

    error: (title: string, description?: string, duration = 6000) =>
      toast({ type: "error", title, description, duration }),

    warning: (title: string, description?: string, duration = 5000) =>
      toast({ type: "warning", title, description, duration }),

    info: (title: string, description?: string, duration = 4000) =>
      toast({ type: "info", title, description, duration }),

    dismiss,
    dismiss_all,
  };
}
