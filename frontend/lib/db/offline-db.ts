import Dexie, { type EntityTable } from "dexie";

// ─── Schema Types ─────────────────────────────────────────────────────────────

export interface CachedPatient {
  id: string;
  tenant_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  document_type: string;
  document_number: string;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  synced_at: number;
}

export interface CachedOdontogramState {
  patient_id: string;
  data: unknown; // Full OdontogramResponse
  synced_at: number;
}

export interface CachedAppointment {
  id: string;
  patient_id: string;
  doctor_id: string;
  patient_name: string | null;
  doctor_name: string | null;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  type: string;
  status: string;
  notes: string | null;
  scheduled_at: string;
  synced_at: number;
}

export interface CachedClinicalRecord {
  id: string;
  patient_id: string;
  doctor_id: string;
  doctor_name: string | null;
  type: string;
  content: Record<string, unknown>;
  tooth_numbers: number[] | null;
  is_editable: boolean;
  created_at: string;
  updated_at: string;
  synced_at: number;
}

export interface PendingSyncItem {
  id?: number; // Auto-incremented
  method: "POST" | "PUT" | "DELETE";
  url: string;
  body: unknown;
  resource: string;
  resource_id: string | null;
  queued_at: number;
  retry_count: number;
}

export interface SyncMetadata {
  resource: string;
  last_synced_at: number;
  last_full_sync_at: number | null;
}

export interface FormDraft {
  key: string;
  data: unknown;
  saved_at: number;
}

export interface QueuedPhoto {
  id?: number; // Auto-incremented
  blob: Blob;
  file_name: string;
  upload_url: string;
  resource: string;
  resource_id: string;
  queued_at: number;
  retry_count: number;
}

// ─── Database ─────────────────────────────────────────────────────────────────

export class DentalOSOfflineDB extends Dexie {
  patients!: EntityTable<CachedPatient, "id">;
  odontogram_states!: EntityTable<CachedOdontogramState, "patient_id">;
  appointments!: EntityTable<CachedAppointment, "id">;
  clinical_records!: EntityTable<CachedClinicalRecord, "id">;
  pending_sync_queue!: EntityTable<PendingSyncItem, "id">;
  sync_metadata!: EntityTable<SyncMetadata, "resource">;
  form_drafts!: EntityTable<FormDraft, "key">;
  photo_queue!: EntityTable<QueuedPhoto, "id">;

  constructor() {
    super("DentalOSOfflineDB");

    this.version(1).stores({
      patients: "id, tenant_id, last_name, document_number, synced_at",
      odontogram_states: "patient_id, synced_at",
      appointments: "id, patient_id, doctor_id, scheduled_at, synced_at",
      clinical_records: "id, patient_id, created_at, synced_at",
      pending_sync_queue: "++id, resource, resource_id, queued_at",
      sync_metadata: "resource",
      form_drafts: "key, saved_at",
    });

    this.version(2).stores({
      patients: "id, tenant_id, last_name, document_number, synced_at",
      odontogram_states: "patient_id, synced_at",
      appointments: "id, patient_id, doctor_id, scheduled_at, synced_at",
      clinical_records: "id, patient_id, created_at, synced_at",
      pending_sync_queue: "++id, resource, resource_id, queued_at",
      sync_metadata: "resource",
      form_drafts: "key, saved_at",
      photo_queue: "++id, resource, resource_id, queued_at",
    });
  }
}

// Singleton instance — coexists with `dentalos-voice` IDB (separate database)
export const offlineDb = new DentalOSOfflineDB();
