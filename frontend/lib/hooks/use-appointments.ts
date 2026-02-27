"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type AppointmentType = "consultation" | "procedure" | "emergency" | "follow_up";

export type AppointmentStatus =
  | "scheduled"
  | "confirmed"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "no_show";

export interface Appointment {
  id: string;
  patient_id: string;
  doctor_id: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  type: AppointmentType;
  status: AppointmentStatus;
  treatment_plan_item_id: string | null;
  cancellation_reason: string | null;
  cancelled_by_patient: boolean;
  no_show_at: string | null;
  completed_at: string | null;
  notes: string | null;
  completion_notes: string | null;
  created_by: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  patient_name: string | null;
  doctor_name: string | null;
}

export interface AppointmentListResponse {
  items: Appointment[];
  total: number;
  next_cursor: string | null;
}

export interface CalendarSlot {
  id: string;
  patient_id: string;
  patient_name: string | null;
  doctor_id: string;
  doctor_name: string | null;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  type: AppointmentType;
  status: AppointmentStatus;
}

export interface CalendarResponse {
  dates: Record<string, CalendarSlot[]>;
  date_from: string;
  date_to: string;
}

export interface AppointmentsQueryParams {
  doctor_id?: string;
  patient_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  cursor?: string;
  page_size?: number;
}

export interface CalendarQueryParams {
  doctor_id?: string;
  date_from: string;
  date_to: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const APPOINTMENTS_KEY = ["appointments"] as const;
export const appointmentKey = (id: string) => ["appointments", id] as const;
export const calendarKey = (params: Record<string, unknown>) =>
  ["appointments", "calendar", params] as const;

// ─── useAppointments ──────────────────────────────────────────────────────────

/**
 * Cursor-paginated list of appointments with optional filters.
 *
 * @example
 * const { data, isLoading } = useAppointments({ doctor_id, date_from, date_to });
 */
export function useAppointments(params: AppointmentsQueryParams = {}) {
  const queryParams: Record<string, unknown> = { page_size: 50, ...params };

  // Strip undefined values so buildQueryString works cleanly
  Object.keys(queryParams).forEach((key) => {
    if (queryParams[key] === undefined) delete queryParams[key];
  });

  return useQuery({
    queryKey: [...APPOINTMENTS_KEY, queryParams],
    queryFn: () =>
      apiGet<AppointmentListResponse>(`/appointments${buildQueryString(queryParams)}`),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useAppointment ───────────────────────────────────────────────────────────

/**
 * Single appointment by ID.
 * Only fetches when id is a non-empty string.
 *
 * @example
 * const { data: appointment, isLoading } = useAppointment(id);
 */
export function useAppointment(id: string | null | undefined) {
  return useQuery({
    queryKey: appointmentKey(id ?? ""),
    queryFn: () => apiGet<Appointment>(`/appointments/${id}`),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

// ─── useCalendar ──────────────────────────────────────────────────────────────

/**
 * Calendar view: appointments grouped by date for a date range.
 * Used by the agenda views (day, week, month).
 *
 * @example
 * const { data: calendar } = useCalendar({ date_from: "2026-02-24", date_to: "2026-02-30" });
 */
export function useCalendar(params: CalendarQueryParams) {
  const queryParams: Record<string, unknown> = { ...params };

  Object.keys(queryParams).forEach((key) => {
    if (queryParams[key] === undefined) delete queryParams[key];
  });

  return useQuery({
    queryKey: calendarKey(queryParams),
    queryFn: () =>
      apiGet<CalendarResponse>(`/appointments/calendar${buildQueryString(queryParams)}`),
    enabled: Boolean(params.date_from) && Boolean(params.date_to),
    staleTime: 60_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useCreateAppointment ─────────────────────────────────────────────────────

/**
 * POST /appointments — creates a new appointment.
 * On success: invalidates appointment and calendar queries, shows toast.
 *
 * @example
 * const { mutate: createAppointment, isPending } = useCreateAppointment();
 * createAppointment(formData, { onSuccess: () => setOpen(false) });
 */
export function useCreateAppointment() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiPost<Appointment>("/appointments", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("Cita agendada", "La cita fue creada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear la cita. Inténtalo de nuevo.";
      error("Error al crear cita", message);
    },
  });
}

// ─── useUpdateAppointment ─────────────────────────────────────────────────────

/**
 * PUT /appointments/{id} — updates an existing appointment.
 * On success: invalidates the appointment and calendar queries.
 *
 * @example
 * const { mutate: updateAppointment } = useUpdateAppointment();
 * updateAppointment({ id, data: { duration_minutes: 60 } });
 */
export function useUpdateAppointment() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      apiPut<Appointment>(`/appointments/${id}`, data),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKey(appointment.id) });
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("Cita actualizada", "Los cambios fueron guardados.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar la cita. Inténtalo de nuevo.";
      error("Error al actualizar cita", message);
    },
  });
}

// ─── useCancelAppointment ─────────────────────────────────────────────────────

/**
 * POST /appointments/{id}/cancel — cancels an appointment with a reason.
 * On success: invalidates related queries.
 *
 * @example
 * const { mutate: cancelAppointment } = useCancelAppointment();
 * cancelAppointment({ id, reason, cancelled_by_patient: false });
 */
export function useCancelAppointment() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      id,
      reason,
      cancelled_by_patient,
    }: {
      id: string;
      reason: string;
      cancelled_by_patient: boolean;
    }) =>
      apiPost<Appointment>(`/appointments/${id}/cancel`, {
        reason,
        cancelled_by_patient,
      }),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKey(appointment.id) });
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("Cita cancelada", "La cita fue cancelada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo cancelar la cita. Inténtalo de nuevo.";
      error("Error al cancelar cita", message);
    },
  });
}

// ─── useConfirmAppointment ────────────────────────────────────────────────────

/**
 * POST /appointments/{id}/confirm — confirms a scheduled appointment.
 * On success: invalidates related queries and shows toast.
 *
 * @example
 * const { mutate: confirmAppointment } = useConfirmAppointment();
 * confirmAppointment(appointmentId);
 */
export function useConfirmAppointment() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (id: string) =>
      apiPost<Appointment>(`/appointments/${id}/confirm`, {}),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKey(appointment.id) });
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("Cita confirmada", "La cita fue confirmada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo confirmar la cita. Inténtalo de nuevo.";
      error("Error al confirmar cita", message);
    },
  });
}

// ─── useStartAppointment ─────────────────────────────────────────────────────

/**
 * POST /appointments/{id}/start — transitions confirmed → in_progress.
 * On success: invalidates related queries and shows toast.
 *
 * @example
 * const { mutate: startAppointment } = useStartAppointment();
 * startAppointment(appointmentId);
 */
export function useStartAppointment() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (id: string) =>
      apiPost<Appointment>(`/appointments/${id}/start`),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKey(appointment.id) });
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("Consulta iniciada", "La cita está ahora en curso.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo iniciar la consulta. Inténtalo de nuevo.";
      error("Error al iniciar consulta", message);
    },
  });
}

// ─── useCompleteAppointment ───────────────────────────────────────────────────

/**
 * POST /appointments/{id}/complete — marks an appointment as completed.
 * On success: invalidates related queries.
 *
 * @example
 * const { mutate: completeAppointment } = useCompleteAppointment();
 * completeAppointment({ id, notes: "Sin novedad" });
 */
export function useCompleteAppointment() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      apiPost<Appointment>(`/appointments/${id}/complete`, { completion_notes: notes }),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKey(appointment.id) });
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("Cita completada", "La cita fue marcada como atendida.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo completar la cita. Inténtalo de nuevo.";
      error("Error al completar cita", message);
    },
  });
}

// ─── useNoShow ────────────────────────────────────────────────────────────────

/**
 * POST /appointments/{id}/no-show — marks a patient as no-show.
 * On success: invalidates related queries.
 *
 * @example
 * const { mutate: markNoShow } = useNoShow();
 * markNoShow(appointmentId);
 */
export function useNoShow() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (id: string) =>
      apiPost<Appointment>(`/appointments/${id}/no-show`, {}),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKey(appointment.id) });
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("No-show registrado", "El paciente fue marcado como ausente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar la ausencia. Inténtalo de nuevo.";
      error("Error al registrar no-show", message);
    },
  });
}

// ─── useRescheduleAppointment ─────────────────────────────────────────────────

/**
 * POST /appointments/{id}/reschedule — moves an appointment to a new time slot.
 * On success: invalidates all appointment and calendar queries.
 *
 * @example
 * const { mutate: reschedule } = useRescheduleAppointment();
 * reschedule({ id, start_time: "2026-03-01T09:00:00Z", duration_minutes: 45 });
 */
export function useRescheduleAppointment() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      id,
      start_time,
      duration_minutes,
    }: {
      id: string;
      start_time: string;
      duration_minutes?: number;
    }) =>
      apiPost<Appointment>(`/appointments/${id}/reschedule`, {
        start_time,
        duration_minutes,
      }),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: appointmentKey(appointment.id) });
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_KEY });
      success("Cita reprogramada", "La cita fue movida al nuevo horario.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo reprogramar la cita. Inténtalo de nuevo.";
      error("Error al reprogramar cita", message);
    },
  });
}
