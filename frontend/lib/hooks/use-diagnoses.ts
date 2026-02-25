"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";
import type { DiagnosisCreate, DiagnosisUpdate } from "@/lib/validations/diagnosis";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DiagnosisResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  cie10_code: string;
  cie10_description: string;
  severity: string;
  status: string;
  tooth_number: number | null;
  notes: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DiagnosisListResponse {
  items: DiagnosisResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const DIAGNOSES_QUERY_KEY = ["diagnoses"] as const;
export const diagnosesQueryKey = (patientId: string, statusFilter?: string) =>
  ["diagnoses", patientId, statusFilter] as const;

// ─── useDiagnoses ─────────────────────────────────────────────────────────────

/**
 * Paginated list of diagnoses for a patient, with optional status filter.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data, isLoading } = useDiagnoses(patientId, "active");
 */
export function useDiagnoses(patientId: string, statusFilter?: string) {
  const queryParams: Record<string, unknown> = {};
  if (statusFilter) queryParams.status = statusFilter;

  return useQuery({
    queryKey: diagnosesQueryKey(patientId, statusFilter),
    queryFn: () =>
      apiGet<DiagnosisListResponse>(
        `/patients/${patientId}/diagnoses${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
  });
}

// ─── useCreateDiagnosis ───────────────────────────────────────────────────────

/**
 * POST /patients/{id}/diagnoses — creates a new diagnosis for a patient.
 * On success: invalidates the diagnoses list for that patient.
 *
 * @example
 * const { mutate: createDiagnosis, isPending } = useCreateDiagnosis(patientId);
 * createDiagnosis(formData, { onSuccess: () => setOpen(false) });
 */
export function useCreateDiagnosis(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: DiagnosisCreate) =>
      apiPost<DiagnosisResponse>(`/patients/${patientId}/diagnoses`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["diagnoses", patientId] });
      success("Diagnóstico creado", "El diagnóstico fue registrado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo crear el diagnóstico. Inténtalo de nuevo.";
      error("Error al crear diagnóstico", message);
    },
  });
}

// ─── useUpdateDiagnosis ───────────────────────────────────────────────────────

/**
 * PUT /patients/{id}/diagnoses/{diagnosisId} — updates an existing diagnosis.
 * On success: invalidates the diagnoses list and shows a success toast.
 *
 * @example
 * const { mutate: updateDiagnosis, isPending } = useUpdateDiagnosis(patientId);
 * updateDiagnosis({ diagnosisId, data: { severity: "moderate" } });
 */
export function useUpdateDiagnosis(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ diagnosisId, data }: { diagnosisId: string; data: DiagnosisUpdate }) =>
      apiPut<DiagnosisResponse>(`/patients/${patientId}/diagnoses/${diagnosisId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["diagnoses", patientId] });
      success("Diagnóstico actualizado", "Los cambios fueron guardados exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar el diagnóstico. Inténtalo de nuevo.";
      error("Error al actualizar diagnóstico", message);
    },
  });
}
