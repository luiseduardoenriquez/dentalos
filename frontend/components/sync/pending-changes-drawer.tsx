"use client";

import { useEffect, useState } from "react";
import { X, Trash2, RefreshCw, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getPendingMutations, discardPendingMutation } from "@/lib/sync/sync-queue";
import { useSyncStatus } from "@/lib/hooks/use-sync-status";
import type { PendingSyncItem } from "@/lib/db/offline-db";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PendingChangesDrawerProps {
  open: boolean;
  onClose: () => void;
}

const RESOURCE_LABELS: Record<string, string> = {
  patients: "Paciente",
  appointments: "Cita",
  clinical_records: "Registro clinico",
  odontogram: "Odontograma",
};

const METHOD_LABELS: Record<string, string> = {
  POST: "Crear",
  PUT: "Actualizar",
  DELETE: "Eliminar",
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Slide-out drawer showing pending offline mutations.
 * Accessible from the SyncStatusIndicator.
 */
export function PendingChangesDrawer({ open, onClose }: PendingChangesDrawerProps) {
  const [items, setItems] = useState<PendingSyncItem[]>([]);
  const { force_sync, pending_count } = useSyncStatus();

  useEffect(() => {
    if (open) {
      getPendingMutations().then(setItems).catch(() => setItems([]));
    }
  }, [open, pending_count]);

  async function handleDiscard(id: number) {
    await discardPendingMutation(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
  }

  async function handleRetryAll() {
    await force_sync();
    const fresh = await getPendingMutations();
    setItems(fresh);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Drawer */}
      <div className="relative z-10 w-full max-w-md bg-white shadow-xl dark:bg-zinc-900 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="text-base font-semibold">Cambios pendientes</h3>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleRetryAll}
              disabled={items.length === 0}
            >
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              Sincronizar
            </Button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1 hover:bg-slate-100 dark:hover:bg-zinc-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto p-4">
          {items.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No hay cambios pendientes
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-primary-600">
                        {METHOD_LABELS[item.method] ?? item.method}
                      </span>
                      <span className="text-sm font-medium truncate">
                        {RESOURCE_LABELS[item.resource] ?? item.resource}
                      </span>
                    </div>
                    <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatTimeAgo(item.queued_at)}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDiscard(item.id!)}
                    className="ml-2 rounded-md p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                    title="Descartar"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatTimeAgo(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "hace menos de 1 min";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.floor(hours / 24)} d`;
}
