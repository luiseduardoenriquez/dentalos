"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BreakSlot {
  /** Start time in HH:MM format (24h) */
  start: string;
  /** End time in HH:MM format (24h) */
  end: string;
}

export interface ScheduleDay {
  /** 0 = Monday … 6 = Sunday (ISO weekday, 0-indexed) */
  day_of_week: number;
  is_working: boolean;
  /** HH:MM or null when not a working day */
  start_time: string | null;
  /** HH:MM or null when not a working day */
  end_time: string | null;
  breaks: BreakSlot[];
  /**
   * Default appointment duration in minutes per appointment type.
   * Keys are appointment type slugs (e.g. "consulta", "limpieza").
   */
  appointment_duration_defaults: Record<string, number>;
}

export interface DoctorSchedule {
  doctor_id: string;
  schedule: ScheduleDay[];
}

export interface AvailabilityBlock {
  id: string;
  doctor_id: string;
  /** ISO 8601 datetime string (UTC) */
  start_time: string;
  /** ISO 8601 datetime string (UTC) */
  end_time: string;
  /** Reason code: e.g. "vacation", "sick_leave", "personal", "training" */
  reason: string;
  description: string | null;
  is_recurring: boolean;
  /** ISO 8601 date string — end date of recurrence, or null */
  recurring_until: string | null;
  created_at: string;
}

export interface AvailabilityBlockCreate {
  start_time: string;
  end_time: string;
  reason: string;
  description?: string | null;
  is_recurring?: boolean;
  recurring_until?: string | null;
}

export interface AvailabilitySlot {
  start_time: string;
  end_time: string;
  available: boolean;
}

export interface AvailabilityResponse {
  doctor_id: string;
  date_from: string;
  date_to: string;
  slot_duration_minutes: number;
  /** Keys are YYYY-MM-DD date strings; values are the time slots for that day */
  slots: Record<string, AvailabilitySlot[]>;
}

export interface AvailableSlotsParams {
  date_from: string;
  date_to: string;
  slot_duration?: number;
  appointment_type?: string;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const scheduleKey = (doctorId: string) =>
  ["schedule", doctorId] as const;

export const blocksKey = (doctorId: string) =>
  ["availability-blocks", doctorId] as const;

export const slotsKey = (
  doctorId: string,
  params: Record<string, unknown>,
) => ["available-slots", doctorId, params] as const;

// ─── useDoctorSchedule ───────────────────────────────────────────────────────

/**
 * Fetches the weekly schedule for a single doctor.
 * Only enabled when doctorId is a non-empty string.
 *
 * @example
 * const { data: schedule, isLoading } = useDoctorSchedule(doctorId);
 */
export function useDoctorSchedule(doctorId: string | null | undefined) {
  return useQuery({
    queryKey: scheduleKey(doctorId ?? ""),
    queryFn: () => apiGet<DoctorSchedule>(`/users/${doctorId}/schedule`),
    enabled: Boolean(doctorId),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// ─── useUpdateSchedule ────────────────────────────────────────────────────────

/**
 * PUT /users/{doctorId}/schedule — saves the full weekly schedule.
 * On success: invalidates the schedule cache and shows a toast.
 *
 * @example
 * const { mutate: updateSchedule, isPending } = useUpdateSchedule();
 * updateSchedule({ doctorId, schedule: days });
 */
export function useUpdateSchedule() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      doctorId,
      schedule,
    }: {
      doctorId: string;
      schedule: ScheduleDay[];
    }) => apiPut<DoctorSchedule>(`/users/${doctorId}/schedule`, { schedule }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: scheduleKey(data.doctor_id) });
      success("Horario actualizado", "El horario de atención fue guardado correctamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo guardar el horario. Inténtalo de nuevo.";
      error("Error al guardar horario", message);
    },
  });
}

// ─── useAvailabilityBlocks ────────────────────────────────────────────────────

/**
 * Fetches unavailability blocks (vacations, leaves, etc.) for a doctor.
 * Optionally filtered by date range.
 * Only enabled when doctorId is a non-empty string.
 *
 * @example
 * const { data: blocks } = useAvailabilityBlocks(doctorId, "2026-03-01", "2026-03-31");
 */
export function useAvailabilityBlocks(
  doctorId: string | null | undefined,
  dateFrom?: string,
  dateTo?: string,
) {
  const params: Record<string, unknown> = {};
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;

  return useQuery({
    queryKey: [...blocksKey(doctorId ?? ""), params],
    queryFn: () =>
      apiGet<AvailabilityBlock[]>(
        `/users/${doctorId}/availability-blocks${buildQueryString(params)}`,
      ),
    enabled: Boolean(doctorId),
    staleTime: 60_000, // 1 minute
  });
}

// ─── useCreateBlock ───────────────────────────────────────────────────────────

/**
 * POST /users/{doctorId}/availability-blocks — creates a new unavailability block.
 * On success: invalidates the blocks list.
 *
 * @example
 * const { mutate: createBlock, isPending } = useCreateBlock();
 * createBlock({ doctorId, data: { start_time, end_time, reason: "vacation" } });
 */
export function useCreateBlock() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      doctorId,
      data,
    }: {
      doctorId: string;
      data: AvailabilityBlockCreate;
    }) =>
      apiPost<AvailabilityBlock>(
        `/users/${doctorId}/availability-blocks`,
        data,
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: blocksKey(variables.doctorId),
      });
      success("Bloqueo creado", "El período de no disponibilidad fue registrado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el bloqueo. Inténtalo de nuevo.";
      error("Error al crear bloqueo", message);
    },
  });
}

// ─── useDeleteBlock ───────────────────────────────────────────────────────────

/**
 * DELETE /users/{doctorId}/availability-blocks/{blockId} — removes an unavailability block.
 * On success: invalidates the blocks list and shows a toast.
 *
 * @example
 * const { mutate: deleteBlock, isPending } = useDeleteBlock();
 * deleteBlock({ doctorId, blockId });
 */
export function useDeleteBlock() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      doctorId,
      blockId,
    }: {
      doctorId: string;
      blockId: string;
    }) =>
      apiDelete<{ message: string }>(
        `/users/${doctorId}/availability-blocks/${blockId}`,
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: blocksKey(variables.doctorId),
      });
      success("Bloqueo eliminado", "El período fue removido del calendario.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo eliminar el bloqueo. Inténtalo de nuevo.";
      error("Error al eliminar bloqueo", message);
    },
  });
}

// ─── useAvailableSlots ────────────────────────────────────────────────────────

/**
 * Fetches available appointment slots for a doctor within a date range.
 * Only enabled when doctorId and both dates are non-empty strings.
 *
 * @example
 * const { data: availability } = useAvailableSlots(doctorId, {
 *   date_from: "2026-03-01",
 *   date_to: "2026-03-07",
 *   slot_duration: 30,
 *   appointment_type: "consulta",
 * });
 */
export function useAvailableSlots(
  doctorId: string | null | undefined,
  params: AvailableSlotsParams,
) {
  const queryParams: Record<string, unknown> = {
    date_from: params.date_from,
    date_to: params.date_to,
  };
  if (params.slot_duration) queryParams.slot_duration = params.slot_duration;
  if (params.appointment_type) queryParams.appointment_type = params.appointment_type;

  return useQuery({
    queryKey: slotsKey(doctorId ?? "", queryParams),
    queryFn: () =>
      apiGet<AvailabilityResponse>(
        `/users/${doctorId}/available-slots${buildQueryString(queryParams)}`,
      ),
    enabled:
      Boolean(doctorId) &&
      Boolean(params.date_from) &&
      Boolean(params.date_to),
    staleTime: 60_000, // 1 minute — slot availability changes frequently
  });
}
