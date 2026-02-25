"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { apiGet, apiPost, apiDelete } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";
import type {
  ConditionCreateValues,
  bulkUpdateSchema,
  snapshotCreateSchema,
  dentitionToggleSchema,
} from "@/lib/validations/odontogram";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface OdontogramCondition {
  id: string;
  tooth_number: number;
  zone: string;
  condition_code: string;
  condition_name: string | null;
  condition_color: string | null;
  severity: string | null;
  notes: string | null;
  source: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ZoneData {
  zone: string;
  condition: OdontogramCondition | null;
}

export interface ToothData {
  tooth_number: number;
  zones: ZoneData[];
  history_count: number;
}

export interface OdontogramResponse {
  patient_id: string;
  dentition_type: string;
  teeth: ToothData[];
  total_conditions: number;
  last_updated: string | null;
}

export interface ConditionUpdateResult {
  condition_id: string;
  action: string;
  previous_condition: Record<string, unknown> | null;
  history_entry_id: string;
}

export interface BulkUpdateResult {
  processed: number;
  added: number;
  updated: number;
  results: ConditionUpdateResult[];
}

export interface HistoryEntry {
  id: string;
  tooth_number: number;
  zone: string;
  action: string;
  condition_code: string;
  previous_data: Record<string, unknown> | null;
  new_data: Record<string, unknown> | null;
  performed_by: string | null;
  performed_by_name: string | null;
  created_at: string;
}

export interface HistoryListResponse {
  items: HistoryEntry[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface SnapshotResponse {
  id: string;
  patient_id: string;
  dentition_type: string;
  label: string | null;
  linked_record_id: string | null;
  linked_treatment_plan_id: string | null;
  created_by: string | null;
  created_at: string;
}

export interface SnapshotDetailResponse extends SnapshotResponse {
  snapshot_data: Record<string, unknown>;
}

export interface SnapshotListResponse {
  items: SnapshotResponse[];
  total: number;
}

export interface CatalogCondition {
  code: string;
  name_es: string;
  name_en: string;
  color_hex: string;
  icon: string;
  zones: string[];
  severity_applicable: boolean;
}

export interface CompareResponse {
  snapshot_a_id: string;
  snapshot_b_id: string;
  added: Record<string, unknown>[];
  removed: Record<string, unknown>[];
  changed: Record<string, unknown>[];
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const ODONTOGRAM_KEY = ["odontogram"] as const;
export const odontogramQueryKey = (patientId: string) => ["odontogram", patientId] as const;
export const odontogramHistoryKey = (patientId: string) => ["odontogram", patientId, "history"] as const;
export const odontogramSnapshotsKey = (patientId: string) => ["odontogram", patientId, "snapshots"] as const;
export const conditionsCatalogKey = ["catalog", "conditions"] as const;

// ─── useOdontogram ────────────────────────────────────────────────────────────

/**
 * Full odontogram state for a patient (all teeth and their current conditions).
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data: odontogram, isLoading } = useOdontogram(patientId);
 */
export function useOdontogram(patientId: string | null | undefined) {
  return useQuery({
    queryKey: odontogramQueryKey(patientId ?? ""),
    queryFn: () => apiGet<OdontogramResponse>(`/patients/${patientId}/odontogram`),
    enabled: Boolean(patientId),
    staleTime: 60_000, // 1 minute — odontogram changes infrequently mid-session
  });
}

// ─── useUpdateCondition ───────────────────────────────────────────────────────

/**
 * POST /patients/{id}/odontogram/conditions — adds or updates a single condition.
 * Invalidates the odontogram cache for that patient on success.
 *
 * @example
 * const { mutate: updateCondition, isPending } = useUpdateCondition();
 * updateCondition({ patientId, data: { tooth_number: 16, zone: "oclusal", condition_code: "caries" } });
 */
export function useUpdateCondition() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: ConditionCreateValues }) =>
      apiPost<ConditionUpdateResult>(`/patients/${patientId}/odontogram/conditions`, data),
    onSuccess: (_data, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: odontogramQueryKey(patientId) });
      success("Condición guardada", "La condición dental fue registrada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo guardar la condición. Inténtalo de nuevo.";
      error("Error al guardar condición", message);
    },
  });
}

// ─── useRemoveCondition ───────────────────────────────────────────────────────

/**
 * DELETE /patients/{id}/odontogram/conditions/{conditionId} — removes a condition.
 * Invalidates the odontogram cache for that patient on success.
 *
 * @example
 * const { mutate: removeCondition, isPending } = useRemoveCondition();
 * removeCondition({ patientId, conditionId });
 */
export function useRemoveCondition() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ patientId, conditionId }: { patientId: string; conditionId: string }) =>
      apiDelete<{ message: string }>(`/patients/${patientId}/odontogram/conditions/${conditionId}`),
    onSuccess: (_data, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: odontogramQueryKey(patientId) });
      success("Condición eliminada", "La condición dental fue removida del odontograma.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo eliminar la condición. Inténtalo de nuevo.";
      error("Error al eliminar condición", message);
    },
  });
}

// ─── useBulkUpdateConditions ──────────────────────────────────────────────────

/**
 * POST /patients/{id}/odontogram/bulk — applies multiple condition updates in one request.
 * Used when saving a full session's worth of changes at once.
 * On success: invalidates the odontogram cache and shows a count-aware toast.
 *
 * @example
 * const { mutate: bulkUpdate, isPending } = useBulkUpdateConditions();
 * bulkUpdate({ patientId, data: { updates: [...], session_notes: "Revisión inicial" } });
 */
export function useBulkUpdateConditions() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      data,
    }: {
      patientId: string;
      data: z.infer<typeof bulkUpdateSchema>;
    }) => apiPost<BulkUpdateResult>(`/patients/${patientId}/odontogram/bulk`, data),
    onSuccess: (result, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: odontogramQueryKey(patientId) });
      success(
        "Odontograma actualizado",
        `Se procesaron ${result.processed} condiciones (${result.added} agregadas, ${result.updated} actualizadas).`,
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar el odontograma. Inténtalo de nuevo.";
      error("Error al actualizar odontograma", message);
    },
  });
}

// ─── useOdontogramHistory ─────────────────────────────────────────────────────

/**
 * Cursor-paginated audit history for a patient's odontogram.
 * Can be filtered by tooth number and/or zone.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data: history, isLoading } = useOdontogramHistory(patientId, { tooth_number: 16 });
 */
export function useOdontogramHistory(
  patientId: string,
  params?: {
    tooth_number?: number;
    zone?: string;
    cursor?: string;
    limit?: number;
  },
) {
  const queryParams: Record<string, unknown> = {};
  if (params?.tooth_number !== undefined) queryParams.tooth_number = params.tooth_number;
  if (params?.zone) queryParams.zone = params.zone;
  if (params?.cursor) queryParams.cursor = params.cursor;
  if (params?.limit !== undefined) queryParams.limit = params.limit;

  return useQuery({
    queryKey: [...odontogramHistoryKey(patientId), queryParams],
    queryFn: () =>
      apiGet<HistoryListResponse>(
        `/patients/${patientId}/odontogram/history${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
  });
}

// ─── useCreateSnapshot ────────────────────────────────────────────────────────

/**
 * POST /patients/{id}/odontogram/snapshots — saves a point-in-time snapshot.
 * Typically called before starting a treatment or generating a clinical record.
 * On success: invalidates the snapshots list.
 *
 * @example
 * const { mutate: createSnapshot, isPending } = useCreateSnapshot();
 * createSnapshot({ patientId, data: { label: "Antes del tratamiento" } });
 */
export function useCreateSnapshot() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      data,
    }: {
      patientId: string;
      data: z.infer<typeof snapshotCreateSchema>;
    }) => apiPost<SnapshotResponse>(`/patients/${patientId}/odontogram/snapshots`, data),
    onSuccess: (_data, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: odontogramSnapshotsKey(patientId) });
      success("Instantánea guardada", "El estado del odontograma fue guardado correctamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo guardar la instantánea. Inténtalo de nuevo.";
      error("Error al guardar instantánea", message);
    },
  });
}

// ─── useOdontogramSnapshots ───────────────────────────────────────────────────

/**
 * List of all snapshots for a patient's odontogram, ordered newest first.
 * Used in the history panel and before/after comparison views.
 *
 * @example
 * const { data: snapshots, isLoading } = useOdontogramSnapshots(patientId);
 */
export function useOdontogramSnapshots(patientId: string) {
  return useQuery({
    queryKey: odontogramSnapshotsKey(patientId),
    queryFn: () =>
      apiGet<SnapshotListResponse>(`/patients/${patientId}/odontogram/snapshots`),
    enabled: Boolean(patientId),
    staleTime: 60_000,
  });
}

// ─── useOdontogramSnapshot ────────────────────────────────────────────────────

/**
 * Single snapshot detail including the full snapshot_data payload.
 * Used when rendering a historical view of the odontogram at a specific point in time.
 *
 * @example
 * const { data: snapshot } = useOdontogramSnapshot(patientId, snapshotId);
 */
export function useOdontogramSnapshot(patientId: string, snapshotId: string) {
  return useQuery({
    queryKey: [...odontogramSnapshotsKey(patientId), snapshotId],
    queryFn: () =>
      apiGet<SnapshotDetailResponse>(
        `/patients/${patientId}/odontogram/snapshots/${snapshotId}`,
      ),
    enabled: Boolean(patientId) && Boolean(snapshotId),
    staleTime: Infinity, // snapshots are immutable — never refetch
  });
}

// ─── useCompareSnapshots ──────────────────────────────────────────────────────

/**
 * Compare two snapshots to show what changed between them (added/removed/changed conditions).
 * Fires immediately when both snapshot IDs are provided.
 *
 * @example
 * const { mutate: compare, data } = useCompareSnapshots();
 * compare({ patientId, snapshot_a_id: "uuid-a", snapshot_b_id: "uuid-b" });
 */
export function useCompareSnapshots() {
  const { error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      snapshot_a_id,
      snapshot_b_id,
    }: {
      patientId: string;
      snapshot_a_id: string;
      snapshot_b_id: string;
    }) =>
      apiGet<CompareResponse>(
        `/patients/${patientId}/odontogram/compare${buildQueryString({ snapshot_a_id, snapshot_b_id })}`,
      ),
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo comparar las instantáneas. Inténtalo de nuevo.";
      error("Error al comparar", message);
    },
  });
}

// ─── useToothDetail ───────────────────────────────────────────────────────────

/**
 * Detailed state of a single tooth: all zones plus their current conditions.
 * Only fetches when both patientId and toothNumber are provided.
 * Used in the tooth detail panel / popover.
 *
 * @example
 * const { data: tooth } = useToothDetail(patientId, selectedTooth);
 */
export function useToothDetail(patientId: string, toothNumber: number | null) {
  return useQuery({
    queryKey: [...odontogramQueryKey(patientId), "teeth", toothNumber],
    queryFn: () =>
      apiGet<ToothData>(`/patients/${patientId}/odontogram/teeth/${toothNumber}`),
    enabled: Boolean(patientId) && toothNumber !== null,
    staleTime: 30_000,
  });
}

// ─── useToggleDentition ───────────────────────────────────────────────────────

/**
 * POST /patients/{id}/odontogram/dentition — switches between adult, pediatric, or mixed dentition.
 * This is a destructive operation that clears incompatible tooth data.
 * On success: invalidates the full odontogram cache.
 *
 * @example
 * const { mutate: toggleDentition, isPending } = useToggleDentition();
 * toggleDentition({ patientId, data: { dentition_type: "pediatric" } });
 */
export function useToggleDentition() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      data,
    }: {
      patientId: string;
      data: z.infer<typeof dentitionToggleSchema>;
    }) => apiPost<OdontogramResponse>(`/patients/${patientId}/odontogram/dentition`, data),
    onSuccess: (_data, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: odontogramQueryKey(patientId) });
      success("Dentición actualizada", "El tipo de dentición fue cambiado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo cambiar la dentición. Inténtalo de nuevo.";
      error("Error al cambiar dentición", message);
    },
  });
}

// ─── useConditionsCatalog ─────────────────────────────────────────────────────

/**
 * Full catalog of available dental conditions with colors, icons, and applicable zones.
 * This is static reference data — it never changes at runtime, so staleTime is Infinity.
 * Used to populate condition pickers and render legend entries.
 *
 * @example
 * const { data: catalog } = useConditionsCatalog();
 */
export function useConditionsCatalog() {
  return useQuery({
    queryKey: conditionsCatalogKey,
    queryFn: () => apiGet<CatalogCondition[]>("/catalog/conditions"),
    staleTime: Infinity, // static catalog — never refetch during a session
  });
}
