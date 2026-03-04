"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CallLogResponse {
  id: string;
  patient_id: string | null;
  phone_number: string;
  direction: "inbound" | "outbound";
  status: "ringing" | "in_progress" | "completed" | "missed" | "voicemail";
  duration_seconds: number | null;
  staff_id: string | null;
  twilio_call_sid: string | null;
  notes: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface CallLogListResponse {
  items: CallLogResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface UpdateCallNotesPayload {
  notes: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const CALLS_QUERY_KEY = ["calls"] as const;

export const callLogsQueryKey = (
  page: number,
  pageSize: number,
  direction?: string,
  status?: string,
) => ["calls", page, pageSize, direction ?? "all", status ?? "all"] as const;

export const callLogQueryKey = (callId: string) =>
  ["calls", callId] as const;

// ─── useCallLogs ──────────────────────────────────────────────────────────────

/**
 * Paginated list of call logs with optional direction and status filters.
 */
export function useCallLogs(
  page: number,
  pageSize: number,
  direction?: string,
  status?: string,
) {
  const queryParams: Record<string, unknown> = {
    page,
    page_size: pageSize,
    ...(direction && direction !== "all" && { direction }),
    ...(status && status !== "all" && { status }),
  };

  return useQuery({
    queryKey: callLogsQueryKey(page, pageSize, direction, status),
    queryFn: () =>
      apiGet<CallLogListResponse>(`/calls${buildQueryString(queryParams)}`),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useUpdateCallNotes ───────────────────────────────────────────────────────

/**
 * PUT /calls/{callId}/notes — updates the notes for a call log entry.
 */
export function useUpdateCallNotes(callId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: UpdateCallNotesPayload) =>
      apiPut<CallLogResponse>(`/calls/${callId}/notes`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CALLS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: callLogQueryKey(callId) });
      success("Notas actualizadas", "Las notas de la llamada fueron guardadas.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudieron guardar las notas. Inténtalo de nuevo.";
      error("Error al guardar notas", message);
    },
  });
}
