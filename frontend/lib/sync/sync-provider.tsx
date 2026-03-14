"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useOnlineStore } from "@/lib/stores/online-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { useToast } from "@/lib/hooks/use-toast";
import { useSwSync } from "@/lib/hooks/use-sw-sync";
import {
  performSync,
  startPeriodicSync,
  stopPeriodicSync,
  setSyncConflictHandler,
} from "./sync-engine";
import { ConflictResolutionModal } from "@/components/sync/conflict-resolution-modal";
import type { ConflictItem, ResolutionChoice } from "./conflict-resolution";

// ─── Context ──────────────────────────────────────────────────────────────────

interface SyncContextValue {
  trigger_sync: () => Promise<void>;
}

const SyncContext = createContext<SyncContextValue>({
  trigger_sync: async () => {},
});

export function useSyncContext() {
  return useContext(SyncContext);
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function SyncProvider({ children }: { children: ReactNode }) {
  const is_online = useOnlineStore((s) => s.is_online);
  const was_online_ref = useRef(is_online);
  const { success, info } = useToast();
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);

  // Listen for SW sync complete messages
  useSwSync();

  // Set up conflict handler
  useEffect(() => {
    setSyncConflictHandler((newConflicts) => {
      setConflicts(newConflicts);
    });
  }, []);

  // Start periodic sync on mount
  useEffect(() => {
    startPeriodicSync();
    return () => stopPeriodicSync();
  }, []);

  // Reconnect orchestration: offline → online transition
  useEffect(() => {
    if (!was_online_ref.current && is_online) {
      // Just came back online
      info("Conexion restaurada", "Sincronizando datos...");

      performSync("delta")
        .then(() => {
          const store = useSyncStore.getState();
          if (store.pending_count === 0) {
            success("Sincronizacion completada", "Todos los cambios fueron sincronizados.");
          }
        })
        .catch(() => {
          // Error already handled in sync engine
        });
    }
    was_online_ref.current = is_online;
  }, [is_online, info, success]);

  // Trigger sync on visibilitychange (fallback for browsers without Background Sync)
  useEffect(() => {
    function handleVisibilityChange() {
      if (document.visibilityState === "visible" && useOnlineStore.getState().is_online) {
        performSync("delta").catch(() => {});
      }
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  // Conflict resolution handlers
  function handleResolveConflicts(
    resolutions: Array<{ conflict: ConflictItem; choice: ResolutionChoice }>,
  ) {
    // For now, just clear conflicts. In a full implementation,
    // "local" choices would re-submit the local data, "server" choices
    // would refresh IDB with server data.
    setConflicts([]);
  }

  function handleDismissConflicts() {
    setConflicts([]);
  }

  const contextValue: SyncContextValue = {
    trigger_sync: () => performSync(),
  };

  return (
    <SyncContext.Provider value={contextValue}>
      {children}
      {conflicts.length > 0 && (
        <ConflictResolutionModal
          conflicts={conflicts}
          onResolve={handleResolveConflicts}
          onDismiss={handleDismissConflicts}
        />
      )}
    </SyncContext.Provider>
  );
}
