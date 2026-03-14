import { apiGet, apiPost } from "@/lib/api-client";
import { useSyncStore } from "@/lib/stores/sync-store";
import { useOnlineStore } from "@/lib/stores/online-store";
import { determineSyncMode } from "./bandwidth-aware";
import { getPendingCount } from "./sync-queue";
import {
  cachePatients,
  cacheAppointments,
  cacheClinicalRecords,
  cacheOdontogramState,
  setLastFullSyncTimestamp,
  getLastFullSyncTimestamp,
  getSyncTimestamp,
  setSyncTimestamp,
} from "@/lib/db/offline-data-service";
import type { CachedPatient, CachedAppointment, CachedClinicalRecord } from "@/lib/db/offline-db";
import type { ConflictItem } from "./conflict-resolution";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SyncDeltaResponse {
  deltas: Array<{
    resource: string;
    items: Record<string, unknown>[];
    total: number;
    synced_at: string;
  }>;
  server_time: string;
}

interface SyncFullResponse {
  patients: Record<string, unknown>[];
  appointments: Record<string, unknown>[];
  odontogram_states: Record<string, unknown>[];
  clinical_records: Record<string, unknown>[];
  server_time: string;
}

interface SyncBatchResponse {
  results: Array<{
    index: number;
    status: "success" | "conflict" | "error";
    resource: string;
    resource_id: string | null;
    server_data: Record<string, unknown> | null;
  }>;
  total: number;
  succeeded: number;
  conflicts: number;
  errors: number;
}

export type SyncMode = "full" | "delta" | "skip";

// ─── Sync Engine ──────────────────────────────────────────────────────────────

let syncTimer: ReturnType<typeof setInterval> | null = null;
let onConflict: ((conflicts: ConflictItem[]) => void) | null = null;

/**
 * Set the conflict handler — called when batch sync produces conflicts.
 */
export function setSyncConflictHandler(handler: (conflicts: ConflictItem[]) => void) {
  onConflict = handler;
}

/**
 * Orchestrate a full sync cycle:
 * 1. Flush pending writes (uploads first)
 * 2. Pull delta or full data (downloads)
 * 3. Handle conflicts
 */
export async function performSync(mode?: SyncMode): Promise<void> {
  const syncMode = mode ?? determineSyncMode();
  if (syncMode === "skip") return;

  const store = useSyncStore.getState();
  store.set_status("syncing");

  try {
    // Step 1: Flush pending writes
    const writeResult = await flushPendingWrites();

    // Step 2: Pull fresh data
    if (syncMode === "full") {
      await pullFull();
    } else {
      await pullDelta();
    }

    // Step 3: Update state
    const pendingCount = await getPendingCount();
    store.set_pending_count(pendingCount);
    store.set_last_synced(Date.now());

    // Step 4: Handle conflicts from batch write
    if (writeResult.conflicts.length > 0 && onConflict) {
      onConflict(writeResult.conflicts);
    }
  } catch (err) {
    store.set_error(err instanceof Error ? err.message : "Error al sincronizar");
  }
}

/**
 * Flush pending offline writes to the server via POST /sync/batch.
 */
export async function flushPendingWrites(): Promise<{ succeeded: number; conflicts: ConflictItem[] }> {
  const { getPendingMutations } = await import("./sync-queue");
  const pending = await getPendingMutations();

  if (pending.length === 0) return { succeeded: 0, conflicts: [] };

  const operations = pending.map((item) => ({
    method: item.method,
    resource: item.resource,
    resource_id: item.resource_id,
    url: item.url,
    body: item.body as Record<string, unknown> | null,
    queued_at: new Date(item.queued_at).toISOString(),
  }));

  try {
    const response = await apiPost<SyncBatchResponse>("/sync/batch", { operations });

    // Remove succeeded items from queue
    const { removePendingMutation } = await import("@/lib/db/offline-data-service");
    for (const result of response.results) {
      if (result.status === "success" || result.status === "conflict") {
        const pendingItem = pending[result.index];
        if (pendingItem?.id) {
          await removePendingMutation(pendingItem.id);
        }
      }
    }

    // Collect conflicts for UI resolution
    const conflicts: ConflictItem[] = response.results
      .filter((r) => r.status === "conflict" && r.server_data)
      .map((r) => ({
        resource: r.resource,
        resource_id: r.resource_id,
        local_data: (pending[r.index]?.body ?? {}) as Record<string, unknown>,
        server_data: r.server_data!,
        queued_at: pending[r.index]?.queued_at ?? Date.now(),
      }));

    return { succeeded: response.succeeded, conflicts };
  } catch {
    // Network error — items stay in queue
    return { succeeded: 0, conflicts: [] };
  }
}

/**
 * Pull delta data from server — only records modified since last sync.
 */
export async function pullDelta(): Promise<void> {
  const sinceTimestamp = await getSyncTimestamp("_global");
  const since = sinceTimestamp
    ? new Date(sinceTimestamp).toISOString()
    : new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

  const response = await apiGet<SyncDeltaResponse>(`/sync/delta?since=${encodeURIComponent(since)}`);
  const now = Date.now();

  for (const delta of response.deltas) {
    await cacheResourceDelta(delta.resource, delta.items, now);
  }

  await setSyncTimestamp("_global", now);
}

/**
 * Pull full data dump from server — used for initial sync or stale cache.
 */
export async function pullFull(): Promise<void> {
  const response = await apiGet<SyncFullResponse>("/sync/full");
  const now = Date.now();

  await cacheResourceDelta("patients", response.patients, now);
  await cacheResourceDelta("appointments", response.appointments, now);
  await cacheResourceDelta("clinical_records", response.clinical_records, now);

  // Odontogram states grouped by patient
  const byPatient = new Map<string, Record<string, unknown>[]>();
  for (const item of response.odontogram_states) {
    const pid = item.patient_id as string;
    if (!byPatient.has(pid)) byPatient.set(pid, []);
    byPatient.get(pid)!.push(item);
  }
  for (const [patientId, conditions] of byPatient) {
    await cacheOdontogramState(patientId, conditions);
  }

  await setLastFullSyncTimestamp(now);
  await setSyncTimestamp("_global", now);
}

/**
 * Start periodic background sync (every 30s).
 */
export function startPeriodicSync(): void {
  if (syncTimer) return;
  syncTimer = setInterval(() => {
    if (useOnlineStore.getState().is_online) {
      performSync().catch(() => {});
    }
  }, 30_000);
}

/**
 * Stop periodic sync.
 */
export function stopPeriodicSync(): void {
  if (syncTimer) {
    clearInterval(syncTimer);
    syncTimer = null;
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function cacheResourceDelta(
  resource: string,
  items: Record<string, unknown>[],
  syncedAt: number,
): Promise<void> {
  if (items.length === 0) return;

  switch (resource) {
    case "patients": {
      const patients: CachedPatient[] = items.map((p) => ({
        id: p.id as string,
        tenant_id: "",
        first_name: (p.first_name as string) ?? "",
        last_name: (p.last_name as string) ?? "",
        full_name: (p.full_name as string) ?? "",
        document_type: (p.document_type as string) ?? "",
        document_number: (p.document_number as string) ?? "",
        phone: (p.phone as string) ?? null,
        email: (p.email as string) ?? null,
        is_active: (p.is_active as boolean) ?? true,
        created_at: (p.created_at as string) ?? "",
        updated_at: (p.updated_at as string) ?? "",
        synced_at: syncedAt,
      }));
      await cachePatients(patients);
      break;
    }
    case "appointments": {
      const appointments: CachedAppointment[] = items.map((a) => ({
        id: a.id as string,
        patient_id: (a.patient_id as string) ?? "",
        doctor_id: (a.doctor_id as string) ?? "",
        patient_name: (a.patient_name as string) ?? null,
        doctor_name: (a.doctor_name as string) ?? null,
        start_time: (a.start_time as string) ?? "",
        end_time: (a.end_time as string) ?? "",
        duration_minutes: (a.duration_minutes as number) ?? 0,
        type: (a.type as string) ?? "",
        status: (a.status as string) ?? "",
        notes: (a.notes as string) ?? null,
        scheduled_at: (a.start_time as string) ?? "",
        synced_at: syncedAt,
      }));
      await cacheAppointments(appointments);
      break;
    }
    case "clinical_records": {
      const records: CachedClinicalRecord[] = items.map((r) => ({
        id: r.id as string,
        patient_id: (r.patient_id as string) ?? "",
        doctor_id: (r.doctor_id as string) ?? "",
        doctor_name: (r.doctor_name as string) ?? null,
        type: (r.type as string) ?? "",
        content: (r.content as Record<string, unknown>) ?? {},
        tooth_numbers: (r.tooth_numbers as number[]) ?? null,
        is_editable: (r.is_editable as boolean) ?? false,
        created_at: (r.created_at as string) ?? "",
        updated_at: (r.updated_at as string) ?? "",
        synced_at: syncedAt,
      }));
      await cacheClinicalRecords(records);
      break;
    }
  }
}
