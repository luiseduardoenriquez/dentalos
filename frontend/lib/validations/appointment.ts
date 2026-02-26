/**
 * Zod validation schemas for appointment forms.
 *
 * These mirror the backend Pydantic schemas for appointment creation.
 * All field names use snake_case to match the backend API.
 *
 * Appointment types (backend API values, spec FE-AG-02):
 * - consultation: Consulta general, 30 min default
 * - procedure: Procedimiento, 60 min default
 * - emergency: Urgencia, 45 min default
 * - follow_up: Control, 20 min default
 */

import { z } from "zod";

// ─── Appointment Types ────────────────────────────────────────────────────────

export const APPOINTMENT_TYPES = [
  "consultation",
  "procedure",
  "emergency",
  "follow_up",
] as const;

export type AppointmentType = (typeof APPOINTMENT_TYPES)[number];

export const APPOINTMENT_TYPE_LABELS: Record<AppointmentType, string> = {
  consultation: "Consulta",
  procedure: "Procedimiento",
  emergency: "Urgencia",
  follow_up: "Control",
};

/** Default duration in minutes per appointment type */
export const APPOINTMENT_TYPE_DURATIONS: Record<AppointmentType, number> = {
  consultation: 30,
  procedure: 60,
  emergency: 45,
  follow_up: 20,
};

// ─── Appointment Statuses ─────────────────────────────────────────────────────

export const APPOINTMENT_STATUSES = [
  "scheduled",
  "confirmed",
  "in_progress",
  "completed",
  "cancelled",
  "no_show",
] as const;

export type AppointmentStatus = (typeof APPOINTMENT_STATUSES)[number];

export const APPOINTMENT_STATUS_LABELS: Record<AppointmentStatus, string> = {
  scheduled: "Programada",
  confirmed: "Confirmada",
  in_progress: "En curso",
  completed: "Completada",
  cancelled: "Cancelada",
  no_show: "No asistió",
};

// ─── Create Schema ────────────────────────────────────────────────────────────

/**
 * Schema for the appointment creation form.
 * Matches POST /api/v1/appointments payload.
 */
export const appointmentCreateSchema = z.object({
  patient_id: z
    .string()
    .min(1, "Selecciona un paciente"),

  doctor_id: z
    .string()
    .min(1, "Selecciona un doctor"),

  // ISO datetime-local string from <input type="datetime-local">
  // e.g. "2026-03-25T10:00"
  start_time: z
    .string()
    .min(1, "Selecciona la fecha y hora")
    .refine((v) => {
      const d = new Date(v);
      return !isNaN(d.getTime());
    }, "Fecha y hora inválidas")
    .refine((v) => {
      return new Date(v) > new Date();
    }, "La cita debe ser en el futuro"),

  type: z.enum(APPOINTMENT_TYPES, {
    errorMap: () => ({ message: "Selecciona un tipo de cita" }),
  }),

  duration_minutes: z
    .number({
      required_error: "Ingresa la duración",
      invalid_type_error: "La duración debe ser un número",
    })
    .min(10, "Duración mínima: 10 minutos")
    .max(240, "Duración máxima: 240 minutos")
    .multipleOf(5, "La duración debe ser múltiplo de 5 minutos"),

  notes: z
    .string()
    .max(500, "Las notas no pueden exceder 500 caracteres")
    .optional()
    .or(z.literal(""))
    .transform((v) => (v === "" ? undefined : v?.trim())),

  treatment_plan_item_id: z
    .string()
    .optional()
    .nullable()
    .transform((v) => v ?? null),

  send_reminder: z.boolean().default(true),
});

export type AppointmentCreateForm = z.infer<typeof appointmentCreateSchema>;

// ─── Cancel Schema ────────────────────────────────────────────────────────────

export const CANCELLATION_REASONS = [
  "paciente_canceló",
  "doctor_canceló",
  "emergencia",
  "reprogramación",
  "otro",
] as const;

export type CancellationReason = (typeof CANCELLATION_REASONS)[number];

export const CANCELLATION_REASON_LABELS: Record<CancellationReason, string> = {
  "paciente_canceló": "Paciente canceló",
  "doctor_canceló": "Doctor no disponible",
  emergencia: "Emergencia médica",
  reprogramación: "Reprogramada para otra fecha",
  otro: "Otro motivo",
};

export const appointmentCancelSchema = z.object({
  reason: z
    .string()
    .min(1, "El motivo de cancelación es requerido")
    .max(500, "El motivo no puede exceder 500 caracteres")
    .transform((v) => v.trim()),

  cancelled_by_patient: z.boolean().default(false),

  notify_patient: z.boolean().default(true),
});

export type AppointmentCancelForm = z.infer<typeof appointmentCancelSchema>;

// ─── Reschedule Schema ────────────────────────────────────────────────────────

export const appointmentRescheduleSchema = z.object({
  start_time: z
    .string()
    .min(1, "Selecciona la nueva fecha y hora")
    .refine((v) => {
      const d = new Date(v);
      return !isNaN(d.getTime());
    }, "Fecha y hora inválidas")
    .refine((v) => {
      return new Date(v) > new Date();
    }, "La cita debe ser en el futuro"),

  duration_minutes: z
    .number({ invalid_type_error: "La duración debe ser un número" })
    .int("La duración debe ser un número entero")
    .min(10, "Duración mínima: 10 minutos")
    .max(240, "Duración máxima: 240 minutos")
    .optional(),
});

export type AppointmentRescheduleForm = z.infer<typeof appointmentRescheduleSchema>;

// ─── Complete Schema ──────────────────────────────────────────────────────────

export const appointmentCompleteSchema = z.object({
  notes: z
    .string()
    .max(1000, "Las notas no pueden exceder 1000 caracteres")
    .optional()
    .or(z.literal(""))
    .transform((v) => (v === "" ? undefined : v?.trim())),
});

export type AppointmentCompleteForm = z.infer<typeof appointmentCompleteSchema>;
