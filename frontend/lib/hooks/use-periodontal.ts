"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PeriodontalMeasurementCreate {
  tooth_number: number;
  site: string;
  pocket_depth: number;
  bleeding_on_probing: boolean;
}

export interface PeriodontalRecordCreate {
  dentition_type: string;
  source: string;
  notes?: string | null;
  measurements: PeriodontalMeasurementCreate[];
}

export interface PeriodontalRecordResponse {
  id: string;
  patient_id: string;
  recorded_by: string;
  dentition_type: string;
  source: string;
  notes: string | null;
  measurement_count: number;
  created_at: string;
  updated_at: string;
}

// ─── useCreatePeriodontalRecord ───────────────────────────────────────────────

export function useCreatePeriodontalRecord(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: PeriodontalRecordCreate) =>
      apiPost<PeriodontalRecordResponse>(
        `/patients/${patientId}/periodontal-records`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["periodontal-records", patientId],
      });
      success(
        "Registro creado",
        "El registro periodontal fue creado exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el registro periodontal. Inténtalo de nuevo.";
      error("Error al crear registro", message);
    },
  });
}
