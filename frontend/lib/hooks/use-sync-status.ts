"use client";

import { useCallback, useEffect } from "react";
import { useSyncStore, type SyncStatus } from "@/lib/stores/sync-store";
import { useOnlineStore } from "@/lib/stores/online-store";
import { getPendingCount, processPendingQueue } from "@/lib/sync/sync-queue";

/**
 * Hook for monitoring sync status and triggering manual sync.
 * Polls pending count every 10s and updates the sync store.
 */
export function useSyncStatus() {
  const status = useSyncStore((s) => s.status);
  const pending_count = useSyncStore((s) => s.pending_count);
  const last_synced_at = useSyncStore((s) => s.last_synced_at);
  const error_message = useSyncStore((s) => s.error_message);
  const is_online = useOnlineStore((s) => s.is_online);

  // Update status based on online state
  useEffect(() => {
    if (!is_online) {
      useSyncStore.getState().set_status("offline");
    } else if (useSyncStore.getState().status === "offline") {
      useSyncStore.getState().set_status("idle");
    }
  }, [is_online]);

  // Poll pending count
  useEffect(() => {
    async function updateCount() {
      try {
        const count = await getPendingCount();
        useSyncStore.getState().set_pending_count(count);
      } catch {
        // IDB error — non-critical
      }
    }
    updateCount();
    const interval = setInterval(updateCount, 10_000);
    return () => clearInterval(interval);
  }, []);

  const force_sync = useCallback(async () => {
    if (!is_online) return;

    useSyncStore.getState().set_status("syncing");
    try {
      const result = await processPendingQueue();
      useSyncStore.getState().set_pending_count(result.total - result.succeeded);
      useSyncStore.getState().set_last_synced(Date.now());
    } catch (err) {
      useSyncStore.getState().set_error(
        err instanceof Error ? err.message : "Error al sincronizar",
      );
    }
  }, [is_online]);

  return {
    status: (is_online ? status : "offline") as SyncStatus,
    pending_count,
    last_synced_at,
    error_message,
    force_sync,
  };
}
