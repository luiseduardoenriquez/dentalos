import { useOnlineStore, type ConnectionEffectiveType } from "@/lib/stores/online-store";

// ─── Types ────────────────────────────────────────────────────────────────────

export type SyncMode = "full" | "delta" | "skip";

// ─── Functions ────────────────────────────────────────────────────────────────

/**
 * Get the current connection type from the online store.
 */
export function getConnectionType(): ConnectionEffectiveType {
  return useOnlineStore.getState().effective_type;
}

/**
 * Determine sync mode based on connection quality.
 * - WiFi/4G: full sync (all resources)
 * - 3G: delta only (minimal data)
 * - 2G/slow-2g: skip sync (too slow)
 * - Offline: skip
 */
export function determineSyncMode(): SyncMode {
  const { is_online, effective_type, is_save_data } = useOnlineStore.getState();

  if (!is_online) return "skip";
  if (is_save_data) return "delta";

  switch (effective_type) {
    case "4g":
    case "unknown": // Unknown = assume good connection
      return "full";
    case "3g":
      return "delta";
    case "2g":
    case "slow-2g":
      return "skip";
    default:
      return "delta";
  }
}
