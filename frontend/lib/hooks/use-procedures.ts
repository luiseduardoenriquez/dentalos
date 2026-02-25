"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";
import type { ProcedureCreate } from "@/lib/validations/procedure";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ProcedureMaterial {
  name: string;
  quantity?: number;
}

export interface ProcedureResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  cups_code: string;
  cups_description: string;
  tooth_number: number | null;
  zones: string[] | null;
  materials_used: ProcedureMaterial[] | null;
  treatment_plan_item_id: string | null;
  clinical_record_id: string | null;
  duration_minutes: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProcedureListResponse {
  items: ProcedureResponse[];
  next_cursor: string | null;
  has_more: boolean;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const PROCEDURES_QUERY_KEY = ["procedures"] as const;
export const proceduresQueryKey = (patientId: string, page: number, pageSize: number) =>
  ["procedures", patientId, page, pageSize] as const;

// ─── useProcedures ────────────────────────────────────────────────────────────

/**
 * Paginated list of procedures performed on a patient.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data, isLoading } = useProcedures(patientId, 1, 20);
 */
export function useProcedures(patientId: string, page: number, pageSize: number) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: proceduresQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<ProcedureListResponse>(
        `/patients/${patientId}/procedures${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useCreateProcedure ───────────────────────────────────────────────────────

/**
 * POST /patients/{id}/procedures — records a new clinical procedure.
 * On success: invalidates the procedures list for that patient.
 *
 * @example
 * const { mutate: createProcedure, isPending } = useCreateProcedure(patientId);
 * createProcedure(formData, { onSuccess: () => setOpen(false) });
 */
export function useCreateProcedure(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: ProcedureCreate) =>
      apiPost<ProcedureResponse>(`/patients/${patientId}/procedures`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["procedures", patientId] });
      success("Procedimiento registrado", "El procedimiento fue guardado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar el procedimiento. Inténtalo de nuevo.";
      error("Error al registrar procedimiento", message);
    },
  });
}
