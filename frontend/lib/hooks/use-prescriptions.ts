"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";
import type { PrescriptionCreate } from "@/lib/validations/prescription";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MedicationItem {
  name: string;
  dosis: string;
  frecuencia: string;
  duracion_dias: number;
  via: string;
  instrucciones: string | null;
}

export interface PrescriptionResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  medications: MedicationItem[];
  diagnosis_id: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PrescriptionListResponse {
  items: PrescriptionResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const PRESCRIPTIONS_QUERY_KEY = ["prescriptions"] as const;
export const prescriptionsQueryKey = (patientId: string, page: number, pageSize: number) =>
  ["prescriptions", patientId, page, pageSize] as const;
export const prescriptionQueryKey = (patientId: string, prescriptionId: string) =>
  ["prescriptions", patientId, prescriptionId] as const;

// ─── usePrescriptions ─────────────────────────────────────────────────────────

/**
 * Paginated list of prescriptions for a patient.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data, isLoading } = usePrescriptions(patientId, 1, 20);
 */
export function usePrescriptions(patientId: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: prescriptionsQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<PrescriptionListResponse>(
        `/patients/${patientId}/prescriptions${buildQueryString({ page, page_size: pageSize })}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── usePrescription ──────────────────────────────────────────────────────────

/**
 * Single prescription by ID.
 * Only fetches when both IDs are non-empty strings.
 *
 * @example
 * const { data: prescription, isLoading } = usePrescription(patientId, prescriptionId);
 */
export function usePrescription(patientId: string, prescriptionId: string) {
  return useQuery({
    queryKey: prescriptionQueryKey(patientId, prescriptionId),
    queryFn: () =>
      apiGet<PrescriptionResponse>(`/patients/${patientId}/prescriptions/${prescriptionId}`),
    enabled: Boolean(patientId) && Boolean(prescriptionId),
    staleTime: 60_000,
  });
}

// ─── useCreatePrescription ────────────────────────────────────────────────────

/**
 * POST /patients/{id}/prescriptions — creates a new prescription for a patient.
 * On success: invalidates the prescriptions list for that patient.
 *
 * @example
 * const { mutate: createPrescription, isPending } = useCreatePrescription(patientId);
 * createPrescription(formData, { onSuccess: (prescription) => router.push(...) });
 */
export function useCreatePrescription(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: PrescriptionCreate) =>
      apiPost<PrescriptionResponse>(`/patients/${patientId}/prescriptions`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prescriptions", patientId] });
      success("Prescripción creada", "La prescripción fue registrada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo crear la prescripción. Inténtalo de nuevo.";
      error("Error al crear prescripción", message);
    },
  });
}

// ─── usePrescriptionPdf ───────────────────────────────────────────────────────

/**
 * Returns a function that fetches the PDF blob for a prescription and opens it
 * in a new browser tab. The function is stateful (tracks loading).
 *
 * @example
 * const { downloadPdf, isDownloading } = usePrescriptionPdf(patientId, prescriptionId);
 * <Button onClick={downloadPdf} disabled={isDownloading}>Descargar PDF</Button>
 */
export function usePrescriptionPdf(patientId: string, prescriptionId: string) {
  const { error } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.get(
        `/patients/${patientId}/prescriptions/${prescriptionId}/pdf`,
        { responseType: "blob" },
      );
      return response.data as Blob;
    },
    onSuccess: (blob: Blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `prescripcion-${prescriptionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      // Revoke the object URL after a short delay to allow the download to start
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo descargar el PDF. Inténtalo de nuevo.";
      error("Error al descargar PDF", message);
    },
  });

  return {
    downloadPdf: () => mutation.mutate(),
    isDownloading: mutation.isPending,
  };
}
