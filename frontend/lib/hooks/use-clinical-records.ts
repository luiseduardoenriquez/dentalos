"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";
import { cacheClinicalRecords, getCachedClinicalRecords } from "@/lib/db/offline-data-service";
import { useOnlineStore } from "@/lib/stores/online-store";
import type { CachedClinicalRecord } from "@/lib/db/offline-db";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ClinicalRecordCreate {
  type: "examination" | "evolution_note" | "procedure";
  content: Record<string, unknown>;
  tooth_numbers?: number[] | null;
  template_id?: string | null;
  template_variables?: Record<string, unknown> | null;
}

export interface ClinicalRecordUpdate {
  content?: Record<string, unknown> | null;
  tooth_numbers?: number[] | null;
}

export interface ClinicalRecordResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  doctor_name: string | null;
  type: string;
  content: Record<string, unknown>;
  tooth_numbers: number[] | null;
  template_id: string | null;
  is_editable: boolean;
  edit_locked_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicalRecordListItem {
  id: string;
  type: string;
  doctor_name: string | null;
  tooth_numbers: number[] | null;
  is_editable: boolean;
  created_at: string;
}

export interface ClinicalRecordListResponse {
  items: ClinicalRecordListItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Anamnesis Types ──────────────────────────────────────────────────────────

export interface AnamnesisSectionData {
  items: string[];
  notes: string;
}

export interface AnamnesisCreate {
  allergies?: AnamnesisSectionData | null;
  medications?: AnamnesisSectionData | null;
  medical_history?: AnamnesisSectionData | null;
  dental_history?: AnamnesisSectionData | null;
  family_history?: AnamnesisSectionData | null;
  habits?: AnamnesisSectionData | null;
}

export interface AnamnesisResponse {
  id: string;
  patient_id: string;
  allergies: AnamnesisSectionData | null;
  medications: AnamnesisSectionData | null;
  medical_history: AnamnesisSectionData | null;
  dental_history: AnamnesisSectionData | null;
  family_history: AnamnesisSectionData | null;
  habits: AnamnesisSectionData | null;
  last_updated_by: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Evolution Template Types ─────────────────────────────────────────────────

export interface EvolutionTemplateStep {
  step_order: number;
  content: string;
}

export interface EvolutionTemplateVariable {
  name: string;
  variable_type: string;
  options: string[] | null;
  is_required: boolean;
}

export interface EvolutionTemplate {
  id: string;
  name: string;
  procedure_type: string;
  cups_code: string | null;
  complexity: string;
  is_builtin: boolean;
}

export interface EvolutionTemplateListResponse {
  items: EvolutionTemplate[];
  total: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const CLINICAL_RECORDS_QUERY_KEY = ["clinical_records"] as const;

export const clinicalRecordsQueryKey = (
  patientId: string,
  page: number,
  pageSize: number,
  type?: string,
) => ["clinical_records", patientId, page, pageSize, type ?? "all"] as const;

export const clinicalRecordQueryKey = (patientId: string, recordId: string) =>
  ["clinical_records", patientId, recordId] as const;

export const anamnesisQueryKey = (patientId: string) =>
  ["anamnesis", patientId] as const;

export const evolutionTemplatesQueryKey = (procedureType?: string) =>
  ["evolution_templates", procedureType ?? "all"] as const;

// ─── useClinicalRecords ──────────────────────────────────────────────────────

/**
 * Paginated list of clinical records for a patient.
 * Optionally filtered by record type.
 *
 * @example
 * const { data, isLoading } = useClinicalRecords(patientId, 1, 20, "examination");
 */
export function useClinicalRecords(
  patientId: string,
  page: number,
  pageSize: number,
  type?: string,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };
  if (type) queryParams.type = type;
  const is_online = useOnlineStore((s) => s.is_online);

  return useQuery({
    queryKey: clinicalRecordsQueryKey(patientId, page, pageSize, type),
    queryFn: async () => {
      // Offline: try IDB cache
      if (!is_online) {
        const cached = await getCachedClinicalRecords(patientId);
        const filtered = type ? cached.filter((r) => r.type === type) : cached;
        const start = (page - 1) * pageSize;
        const paged = filtered.slice(start, start + pageSize);
        return {
          items: paged as unknown as ClinicalRecordListItem[],
          total: filtered.length,
          page,
          page_size: pageSize,
        } as ClinicalRecordListResponse;
      }
      const result = await apiGet<ClinicalRecordListResponse>(
        `/patients/${patientId}/clinical-records${buildQueryString(queryParams)}`,
      );
      // Write-through to IDB
      try {
        const now = Date.now();
        const toCache: CachedClinicalRecord[] = result.items.map((r) => ({
          id: r.id,
          patient_id: patientId,
          doctor_id: "",
          doctor_name: r.doctor_name,
          type: r.type,
          content: {},
          tooth_numbers: r.tooth_numbers,
          is_editable: r.is_editable,
          created_at: r.created_at,
          updated_at: "",
          synced_at: now,
        }));
        cacheClinicalRecords(toCache).catch(() => {});
      } catch {
        // Non-blocking
      }
      return result;
    },
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useClinicalRecord ───────────────────────────────────────────────────────

/**
 * Single clinical record by ID.
 *
 * @example
 * const { data: record, isLoading } = useClinicalRecord(patientId, recordId);
 */
export function useClinicalRecord(patientId: string, recordId: string) {
  return useQuery({
    queryKey: clinicalRecordQueryKey(patientId, recordId),
    queryFn: () =>
      apiGet<ClinicalRecordResponse>(
        `/patients/${patientId}/clinical-records/${recordId}`,
      ),
    enabled: Boolean(patientId) && Boolean(recordId),
    staleTime: 60_000,
  });
}

// ─── useCreateClinicalRecord ─────────────────────────────────────────────────

/**
 * POST /patients/{id}/clinical-records — creates a new clinical record.
 * On success: invalidates clinical_records list and medical-history queries.
 *
 * @example
 * const { mutate: createRecord, isPending } = useCreateClinicalRecord(patientId);
 * createRecord({ type: "examination", content: { html: "..." } });
 */
export function useCreateClinicalRecord(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: ClinicalRecordCreate) =>
      apiPost<ClinicalRecordResponse>(
        `/patients/${patientId}/clinical-records`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["clinical_records", patientId],
      });
      queryClient.invalidateQueries({
        queryKey: ["medical-history", patientId],
      });
      success(
        "Registro creado",
        "El registro clínico fue creado exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el registro clínico. Inténtalo de nuevo.";
      error("Error al crear registro", message);
    },
  });
}

// ─── useUpdateClinicalRecord ─────────────────────────────────────────────────

/**
 * PUT /patients/{id}/clinical-records/{recordId} — updates an existing record.
 * Records can only be edited within the 24-hour edit window.
 *
 * @example
 * const { mutate: updateRecord, isPending } = useUpdateClinicalRecord(patientId);
 * updateRecord({ recordId, data: { content: { html: "..." } } });
 */
export function useUpdateClinicalRecord(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      recordId,
      data,
    }: {
      recordId: string;
      data: ClinicalRecordUpdate;
    }) =>
      apiPut<ClinicalRecordResponse>(
        `/patients/${patientId}/clinical-records/${recordId}`,
        data,
      ),
    onSuccess: (record) => {
      queryClient.invalidateQueries({
        queryKey: clinicalRecordQueryKey(patientId, record.id),
      });
      queryClient.invalidateQueries({
        queryKey: ["clinical_records", patientId],
      });
      success("Registro actualizado", "Los cambios fueron guardados exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar el registro. Inténtalo de nuevo.";
      error("Error al actualizar registro", message);
    },
  });
}

// ─── useAnamnesis ────────────────────────────────────────────────────────────

/**
 * GET /patients/{id}/anamnesis — fetches the patient's anamnesis.
 * Handles 404 as "no anamnesis yet" (returns undefined data, no error).
 *
 * @example
 * const { data: anamnesis, isLoading } = useAnamnesis(patientId);
 */
export function useAnamnesis(patientId: string) {
  return useQuery({
    queryKey: anamnesisQueryKey(patientId),
    queryFn: async () => {
      try {
        return await apiGet<AnamnesisResponse>(
          `/patients/${patientId}/anamnesis`,
        );
      } catch (err: unknown) {
        // 404 means no anamnesis exists yet — return null instead of erroring
        if (
          err &&
          typeof err === "object" &&
          "response" in err &&
          (err as { response?: { status?: number } }).response?.status === 404
        ) {
          return null;
        }
        throw err;
      }
    },
    enabled: Boolean(patientId),
    staleTime: 60_000,
  });
}

// ─── useUpsertAnamnesis ──────────────────────────────────────────────────────

/**
 * POST /patients/{id}/anamnesis — creates or updates the patient's anamnesis.
 * On success: invalidates anamnesis and medical-history queries.
 *
 * @example
 * const { mutate: upsertAnamnesis, isPending } = useUpsertAnamnesis(patientId);
 * upsertAnamnesis({ allergies: { items: ["Penicilina"], notes: "" } });
 */
export function useUpsertAnamnesis(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: AnamnesisCreate) =>
      apiPost<AnamnesisResponse>(
        `/patients/${patientId}/anamnesis`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: anamnesisQueryKey(patientId),
      });
      queryClient.invalidateQueries({
        queryKey: ["medical-history", patientId],
      });
      success(
        "Anamnesis guardada",
        "La anamnesis del paciente fue actualizada exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo guardar la anamnesis. Inténtalo de nuevo.";
      error("Error al guardar anamnesis", message);
    },
  });
}

// ─── useEvolutionTemplates ───────────────────────────────────────────────────

/**
 * GET /evolution-templates — fetches available evolution templates.
 * Optionally filtered by procedure type.
 *
 * @example
 * const { data, isLoading } = useEvolutionTemplates("endodoncia");
 */
export function useEvolutionTemplates(procedureType?: string) {
  const queryParams: Record<string, unknown> = {};
  if (procedureType) queryParams.procedure_type = procedureType;

  return useQuery({
    queryKey: evolutionTemplatesQueryKey(procedureType),
    queryFn: () =>
      apiGet<EvolutionTemplateListResponse>(
        `/evolution-templates${buildQueryString(queryParams)}`,
      ),
    staleTime: 5 * 60_000, // 5 minutes — templates change rarely
  });
}
