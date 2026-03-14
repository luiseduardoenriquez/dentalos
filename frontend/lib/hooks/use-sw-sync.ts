"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSyncStore } from "@/lib/stores/sync-store";
import { getPendingCount } from "@/lib/sync/sync-queue";
import { useToast } from "@/lib/hooks/use-toast";

/**
 * Listens for SYNC_COMPLETE messages from the service worker.
 * Invalidates React Query caches and updates sync status.
 */
export function useSwSync() {
  const queryClient = useQueryClient();
  const { success } = useToast();

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.data?.type === "SYNC_COMPLETE") {
        const count = event.data.count ?? 0;

        // Invalidate relevant queries to pick up synced data
        queryClient.invalidateQueries({ queryKey: ["patients"] });
        queryClient.invalidateQueries({ queryKey: ["appointments"] });
        queryClient.invalidateQueries({ queryKey: ["clinical_records"] });
        queryClient.invalidateQueries({ queryKey: ["odontogram"] });

        // Update sync store
        useSyncStore.getState().set_last_synced(Date.now());
        getPendingCount().then((pending) => {
          useSyncStore.getState().set_pending_count(pending);
        }).catch(() => {});

        if (count > 0) {
          success(
            "Sincronizacion completada",
            `${count} ${count === 1 ? "cambio sincronizado" : "cambios sincronizados"}.`,
          );
        }
      }
    }

    navigator.serviceWorker?.addEventListener("message", handleMessage);
    return () => {
      navigator.serviceWorker?.removeEventListener("message", handleMessage);
    };
  }, [queryClient, success]);
}
