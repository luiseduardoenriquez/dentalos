// ─── Types ────────────────────────────────────────────────────────────────────

export interface ConflictItem {
  resource: string;
  resource_id: string | null;
  local_data: Record<string, unknown>;
  server_data: Record<string, unknown>;
  queued_at: number;
}

export type ResolutionChoice = "local" | "server";

// ─── Generic LWW Resolution ──────────────────────────────────────────────────

/**
 * Last-Write-Wins resolution for generic resources.
 * Returns the data set with the more recent timestamp.
 */
export function resolveLastWriteWins(
  local: Record<string, unknown>,
  server: Record<string, unknown>,
): Record<string, unknown> {
  const localTime = new Date(local.updated_at as string).getTime();
  const serverTime = new Date(server.updated_at as string).getTime();
  return serverTime >= localTime ? server : local;
}

// ─── Odontogram Surface-Level Merge ──────────────────────────────────────────

interface OdontogramCondition {
  tooth_number: number;
  zone: string;
  condition_code: string;
  updated_at: string;
  [key: string]: unknown;
}

/**
 * Merge odontogram states at the surface level.
 * For each tooth+zone combination, keep whichever version is newer.
 * This allows non-overlapping changes to merge cleanly.
 */
export function mergeOdontogramStates(
  clientConditions: OdontogramCondition[],
  serverConditions: OdontogramCondition[],
): OdontogramCondition[] {
  const merged = new Map<string, OdontogramCondition>();

  // Add all server conditions first
  for (const condition of serverConditions) {
    const key = `${condition.tooth_number}-${condition.zone}`;
    merged.set(key, condition);
  }

  // Overlay client conditions where they are newer
  for (const condition of clientConditions) {
    const key = `${condition.tooth_number}-${condition.zone}`;
    const existing = merged.get(key);

    if (!existing) {
      // New condition from client
      merged.set(key, condition);
    } else {
      // Compare timestamps — keep newer
      const clientTime = new Date(condition.updated_at).getTime();
      const serverTime = new Date(existing.updated_at).getTime();
      if (clientTime > serverTime) {
        merged.set(key, condition);
      }
    }
  }

  return Array.from(merged.values());
}
