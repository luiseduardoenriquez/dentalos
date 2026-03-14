"use client";

import type { ReactNode } from "react";
import { WifiOff } from "lucide-react";
import { useOnlineStore } from "@/lib/stores/online-store";

interface OfflineFeatureGateProps {
  children: ReactNode;
  /** Custom message when feature is unavailable offline */
  message?: string;
  /** If true, render children in a dimmed/disabled state instead of replacing */
  dim_mode?: boolean;
}

/**
 * Wrapper that disables features requiring internet connectivity.
 * Used for: invoices (DIAN), scheduling (create), analytics,
 * WhatsApp/SMS, portal features.
 *
 * @example
 * <OfflineFeatureGate>
 *   <InvoiceForm />
 * </OfflineFeatureGate>
 */
export function OfflineFeatureGate({
  children,
  message = "Esta funcion requiere conexion a internet",
  dim_mode = false,
}: OfflineFeatureGateProps) {
  const is_online = useOnlineStore((s) => s.is_online);

  if (is_online) return <>{children}</>;

  if (dim_mode) {
    return (
      <div className="relative">
        <div className="pointer-events-none opacity-40">{children}</div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex items-center gap-2 rounded-lg bg-white/90 px-4 py-2 shadow-md dark:bg-zinc-900/90">
            <WifiOff className="h-4 w-4 text-amber-500" />
            <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
              {message}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <WifiOff className="mb-3 h-10 w-10 text-amber-400" />
      <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
        {message}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Reconecta a internet para acceder a esta funcion.
      </p>
    </div>
  );
}
