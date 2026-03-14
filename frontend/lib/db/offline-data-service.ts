import {
  offlineDb,
  type CachedPatient,
  type CachedAppointment,
  type CachedClinicalRecord,
  type CachedOdontogramState,
  type PendingSyncItem,
  type FormDraft,
} from "./offline-db";

// ─── Constants ────────────────────────────────────────────────────────────────

const MAX_CACHED_PATIENTS = 200;
const MAX_CACHED_CLINICAL_RECORDS_DAYS = 7;

// ─── Patients ─────────────────────────────────────────────────────────────────

export async function cachePatients(patients: CachedPatient[]): Promise<void> {
  await offlineDb.patients.bulkPut(patients);
  // Prune to keep only the most recent MAX_CACHED_PATIENTS
  const count = await offlineDb.patients.count();
  if (count > MAX_CACHED_PATIENTS) {
    const toRemove = await offlineDb.patients
      .orderBy("synced_at")
      .limit(count - MAX_CACHED_PATIENTS)
      .primaryKeys();
    await offlineDb.patients.bulkDelete(toRemove);
  }
}

export async function getCachedPatients(
  search?: string,
): Promise<CachedPatient[]> {
  if (!search) {
    return offlineDb.patients.orderBy("last_name").limit(MAX_CACHED_PATIENTS).toArray();
  }
  const q = search.toLowerCase();
  return offlineDb.patients
    .filter(
      (p) =>
        p.full_name.toLowerCase().includes(q) ||
        p.document_number.includes(q),
    )
    .limit(50)
    .toArray();
}

export async function getCachedPatient(id: string): Promise<CachedPatient | undefined> {
  return offlineDb.patients.get(id);
}

// ─── Odontogram ───────────────────────────────────────────────────────────────

export async function cacheOdontogramState(
  patient_id: string,
  data: unknown,
): Promise<void> {
  await offlineDb.odontogram_states.put({
    patient_id,
    data,
    synced_at: Date.now(),
  });
}

export async function getCachedOdontogramState(
  patient_id: string,
): Promise<CachedOdontogramState | undefined> {
  return offlineDb.odontogram_states.get(patient_id);
}

// ─── Appointments ─────────────────────────────────────────────────────────────

export async function cacheAppointments(
  appointments: CachedAppointment[],
): Promise<void> {
  await offlineDb.appointments.bulkPut(appointments);
}

export async function getCachedAppointments(
  filters?: { doctor_id?: string; date_from?: string; date_to?: string },
): Promise<CachedAppointment[]> {
  let collection = offlineDb.appointments.orderBy("scheduled_at");

  if (filters?.doctor_id || filters?.date_from || filters?.date_to) {
    return collection
      .filter((a) => {
        if (filters.doctor_id && a.doctor_id !== filters.doctor_id) return false;
        if (filters.date_from && a.start_time < filters.date_from) return false;
        if (filters.date_to && a.start_time > filters.date_to) return false;
        return true;
      })
      .toArray();
  }

  return collection.toArray();
}

// ─── Clinical Records ─────────────────────────────────────────────────────────

export async function cacheClinicalRecords(
  records: CachedClinicalRecord[],
): Promise<void> {
  await offlineDb.clinical_records.bulkPut(records);
}

export async function getCachedClinicalRecords(
  patient_id: string,
): Promise<CachedClinicalRecord[]> {
  return offlineDb.clinical_records
    .where("patient_id")
    .equals(patient_id)
    .reverse()
    .sortBy("created_at");
}

// ─── Sync Metadata ────────────────────────────────────────────────────────────

export async function getSyncTimestamp(
  resource: string,
): Promise<number | null> {
  const meta = await offlineDb.sync_metadata.get(resource);
  return meta?.last_synced_at ?? null;
}

export async function setSyncTimestamp(
  resource: string,
  timestamp: number,
): Promise<void> {
  await offlineDb.sync_metadata.put({
    resource,
    last_synced_at: timestamp,
    last_full_sync_at:
      (await offlineDb.sync_metadata.get(resource))?.last_full_sync_at ?? null,
  });
}

export async function getLastFullSyncTimestamp(): Promise<number | null> {
  const meta = await offlineDb.sync_metadata.get("_global");
  return meta?.last_full_sync_at ?? null;
}

export async function setLastFullSyncTimestamp(timestamp: number): Promise<void> {
  const existing = await offlineDb.sync_metadata.get("_global");
  await offlineDb.sync_metadata.put({
    resource: "_global",
    last_synced_at: existing?.last_synced_at ?? timestamp,
    last_full_sync_at: timestamp,
  });
}

// ─── Pending Sync Queue ───────────────────────────────────────────────────────

export async function queueMutation(
  item: Omit<PendingSyncItem, "id">,
): Promise<number> {
  return offlineDb.pending_sync_queue.add(item as PendingSyncItem) as Promise<number>;
}

export async function getPendingMutations(): Promise<PendingSyncItem[]> {
  return offlineDb.pending_sync_queue.orderBy("queued_at").toArray();
}

export async function getPendingCount(): Promise<number> {
  return offlineDb.pending_sync_queue.count();
}

export async function removePendingMutation(id: number): Promise<void> {
  await offlineDb.pending_sync_queue.delete(id);
}

export async function clearPendingMutations(): Promise<void> {
  await offlineDb.pending_sync_queue.clear();
}

// ─── Form Drafts (IDB version) ───────────────────────────────────────────────

export async function saveDraft(key: string, data: unknown): Promise<void> {
  await offlineDb.form_drafts.put({ key, data, saved_at: Date.now() });
}

export async function getDraft(key: string): Promise<FormDraft | undefined> {
  return offlineDb.form_drafts.get(key);
}

export async function removeDraft(key: string): Promise<void> {
  await offlineDb.form_drafts.delete(key);
}

// ─── Data Pruning ─────────────────────────────────────────────────────────────

export async function pruneOldData(): Promise<void> {
  const cutoff = Date.now() - MAX_CACHED_CLINICAL_RECORDS_DAYS * 24 * 60 * 60 * 1000;

  // Prune old clinical records
  const oldRecords = await offlineDb.clinical_records
    .where("synced_at")
    .below(cutoff)
    .primaryKeys();
  if (oldRecords.length > 0) {
    await offlineDb.clinical_records.bulkDelete(oldRecords);
  }

  // Prune old appointments (older than 7 days)
  const oldAppointments = await offlineDb.appointments
    .where("synced_at")
    .below(cutoff)
    .primaryKeys();
  if (oldAppointments.length > 0) {
    await offlineDb.appointments.bulkDelete(oldAppointments);
  }
}

// ─── Full Wipe (logout / tenant switch) ───────────────────────────────────────

export async function clearAllOfflineData(): Promise<void> {
  await Promise.all([
    offlineDb.patients.clear(),
    offlineDb.odontogram_states.clear(),
    offlineDb.appointments.clear(),
    offlineDb.clinical_records.clear(),
    offlineDb.pending_sync_queue.clear(),
    offlineDb.sync_metadata.clear(),
    offlineDb.form_drafts.clear(),
    offlineDb.photo_queue.clear(),
  ]);
}
