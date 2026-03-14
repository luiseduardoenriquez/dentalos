"use client";

import { useSyncStatus } from "@/lib/hooks/use-sync-status";
import { cn } from "@/lib/utils";

const STATUS_CONFIG = {
  synced: { color: "bg-emerald-500", label: "Sincronizado", pulse: false },
  syncing: { color: "bg-blue-500", label: "Sincronizando...", pulse: true },
  idle: { color: "bg-emerald-500", label: "Al dia", pulse: false },
  offline: { color: "bg-amber-500", label: "Sin conexion", pulse: false },
  error: { color: "bg-red-500", label: "Error de sincronizacion", pulse: false },
} as const;

/**
 * Small colored dot in the dashboard header indicating sync status.
 * Shows pending count when there are queued offline mutations.
 */
export function SyncStatusIndicator() {
  const { status, pending_count } = useSyncStatus();
  const config = STATUS_CONFIG[status];

  return (
    <div className="flex items-center gap-1.5" title={config.label}>
      <span className="relative flex h-2.5 w-2.5">
        {config.pulse && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping",
              config.color,
            )}
          />
        )}
        <span
          className={cn(
            "relative inline-flex h-2.5 w-2.5 rounded-full",
            config.color,
          )}
        />
      </span>
      {pending_count > 0 && (
        <span className="text-xs text-muted-foreground tabular-nums">
          {pending_count}
        </span>
      )}
    </div>
  );
}
