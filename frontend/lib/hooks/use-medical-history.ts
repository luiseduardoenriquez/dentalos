"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type MedicalHistoryEventType =
  | "diagnosis"
  | "procedure"
  | "clinical_record"
  | "prescription"
  | "consent";

export interface MedicalHistoryEvent {
  id: string;
  event_type: MedicalHistoryEventType;
  event_date: string;
  title: string;
  description: string;
  doctor_name?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface MedicalHistoryResponse {
  items: MedicalHistoryEvent[];
  next_cursor: string | null;
  has_more: boolean;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const MEDICAL_HISTORY_QUERY_KEY = ["medical-history"] as const;
export const medicalHistoryQueryKey = (patientId: string, cursor?: string) =>
  ["medical-history", patientId, cursor ?? "initial"] as const;

// ─── useMedicalHistory ────────────────────────────────────────────────────────

/**
 * Cursor-paginated unified medical history timeline for a patient.
 * Returns events of all types (diagnoses, procedures, records, prescriptions, consents)
 * ordered newest first. Only fetches when patientId is a non-empty string.
 *
 * Pass `cursor` from the previous response's `next_cursor` field to load the next page.
 *
 * @example
 * // Initial page
 * const { data } = useMedicalHistory(patientId);
 *
 * // Next page
 * const { data: nextPage } = useMedicalHistory(patientId, data?.next_cursor ?? undefined);
 */
export function useMedicalHistory(patientId: string, cursor?: string) {
  const queryParams: Record<string, unknown> = { page_size: 20 };
  if (cursor) queryParams.cursor = cursor;

  return useQuery({
    queryKey: medicalHistoryQueryKey(patientId, cursor),
    queryFn: () =>
      apiGet<MedicalHistoryResponse>(
        `/patients/${patientId}/medical-history${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
  });
}
