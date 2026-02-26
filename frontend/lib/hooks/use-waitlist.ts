"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type WaitlistStatus = "waiting" | "notified" | "scheduled" | "expired" | "cancelled";

export interface WaitlistEntry {
  id: string;
  patient_id: string;
  preferred_doctor_id: string | null;
  /** Appointment type slug, e.g. "consulta", "limpieza" */
  procedure_type: string | null;
  /** ISO weekday numbers (0=Monday … 6=Sunday) */
  preferred_days: number[];
  /** Preferred start of time window: HH:MM or null */
  preferred_time_from: string | null;
  /** Preferred end of time window: HH:MM or null */
  preferred_time_to: string | null;
  /** ISO 8601 date — entry expires after this date */
  valid_until: string | null;
  status: WaitlistStatus;
  notification_count: number;
  last_notified_at: string | null;
  created_at: string;
  /** Denormalized for display — populated by the API join */
  patient_name: string | null;
  /** Denormalized for display */
  preferred_doctor_name: string | null;
}

export interface WaitlistEntryCreate {
  patient_id: string;
  preferred_doctor_id?: string | null;
  procedure_type?: string | null;
  /** ISO weekday numbers (0=Monday … 6=Sunday) */
  preferred_days?: number[];
  preferred_time_from?: string | null;
  preferred_time_to?: string | null;
  /** ISO 8601 date */
  valid_until?: string | null;
}

export interface WaitlistListResponse {
  items: WaitlistEntry[];
  total: number;
  /** Opaque cursor for next page, or null when no more pages */
  next_cursor: string | null;
}

export interface WaitlistQueryParams {
  status?: WaitlistStatus;
  doctor_id?: string;
  cursor?: string;
  page_size?: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const WAITLIST_KEY = ["waitlist"] as const;

export const waitlistKey = (params: WaitlistQueryParams) =>
  [...WAITLIST_KEY, params] as const;

// ─── useWaitlist ──────────────────────────────────────────────────────────────

/**
 * Cursor-paginated list of waitlist entries, optionally filtered by status or doctor.
 *
 * @example
 * const { data, isLoading } = useWaitlist({ status: "waiting", page_size: 20 });
 */
export function useWaitlist(params: WaitlistQueryParams = {}) {
  const { status, doctor_id, cursor, page_size = 20 } = params;

  const queryParams: Record<string, unknown> = { page_size };
  if (status) queryParams.status = status;
  if (doctor_id) queryParams.doctor_id = doctor_id;
  if (cursor) queryParams.cursor = cursor;

  return useQuery({
    queryKey: waitlistKey(params),
    queryFn: () =>
      apiGet<WaitlistListResponse>(`/waitlist${buildQueryString(queryParams)}`),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useAddToWaitlist ─────────────────────────────────────────────────────────

/**
 * POST /waitlist — adds a patient to the waitlist.
 * On success: invalidates the waitlist cache so the new entry appears immediately.
 *
 * @example
 * const { mutate: addToWaitlist, isPending } = useAddToWaitlist();
 * addToWaitlist(
 *   { patient_id, preferred_doctor_id, preferred_days: [0, 1, 4] },
 *   { onSuccess: () => setOpen(false) }
 * );
 */
export function useAddToWaitlist() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: WaitlistEntryCreate) =>
      apiPost<WaitlistEntry>("/waitlist", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WAITLIST_KEY });
      success(
        "Paciente agregado a lista de espera",
        "El paciente será notificado cuando haya disponibilidad.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo agregar el paciente. Inténtalo de nuevo.";
      error("Error al agregar a lista de espera", message);
    },
  });
}

// ─── useNotifyWaitlistEntry ───────────────────────────────────────────────────

/**
 * POST /waitlist/{id}/notify — sends a notification to the patient for a waitlist slot.
 * On success: invalidates the waitlist so the notification_count updates immediately.
 *
 * @example
 * const { mutate: notify, isPending } = useNotifyWaitlistEntry();
 * notify(entryId);
 */
export function useNotifyWaitlistEntry() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (entryId: string) =>
      apiPost<WaitlistEntry>(`/waitlist/${entryId}/notify`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: WAITLIST_KEY });
      success(
        "Notificación enviada",
        "Se notificó al paciente sobre la disponibilidad.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo enviar la notificación. Inténtalo de nuevo.";
      error("Error al notificar", message);
    },
  });
}
