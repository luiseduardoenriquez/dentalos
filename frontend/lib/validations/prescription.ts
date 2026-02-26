/**
 * Zod validation schemas for prescription forms.
 *
 * These mirror the backend Pydantic schemas for prescription creation.
 * All field names use snake_case to match the backend API.
 */

import { z } from "zod";

// ─── Via (Route of Administration) ────────────────────────────────────────────

export const VIA_OPTIONS = [
  "oral",
  "sublingual",
  "topica",
  "intramuscular",
  "intravenosa",
  "rectal",
] as const;

export type Via = (typeof VIA_OPTIONS)[number];

export const VIA_LABELS: Record<string, string> = {
  oral: "Oral",
  sublingual: "Sublingual",
  topica: "Tópica",
  intramuscular: "Intramuscular",
  intravenosa: "Intravenosa",
  rectal: "Rectal",
};

// ─── Medication Item Schema ────────────────────────────────────────────────────

/**
 * Schema for a single medication entry within a prescription.
 */
export const medicationItemSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Nombre requerido")
    .max(200, "El nombre no puede exceder 200 caracteres"),

  dosis: z
    .string()
    .trim()
    .min(1, "Dosis requerida")
    .max(100, "La dosis no puede exceder 100 caracteres"),

  frecuencia: z
    .string()
    .trim()
    .min(1, "Frecuencia requerida")
    .max(100, "La frecuencia no puede exceder 100 caracteres"),

  duracion_dias: z.coerce
    .number({ invalid_type_error: "Ingresa un número de días válido" })
    .int("La duración debe ser un número entero")
    .min(1, "Mínimo 1 día")
    .max(365, "Máximo 365 días"),

  via: z.string().max(30, "Vía de administración inválida").default("oral"),

  instrucciones: z
    .string()
    .max(500, "Las instrucciones no pueden exceder 500 caracteres")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),
});

export interface MedicationItemFormValues {
  name: string;
  dosis: string;
  frecuencia: string;
  duracion_dias: number;
  via: string;
  instrucciones: string | null;
}

// ─── Prescription Create Schema ───────────────────────────────────────────────

/**
 * Schema for creating a new prescription.
 * Mirrors the backend PrescriptionCreate Pydantic schema.
 */
export const prescriptionCreateSchema = z.object({
  medications: z
    .array(medicationItemSchema)
    .min(1, "Agregue al menos un medicamento")
    .max(20, "Se permiten máximo 20 medicamentos"),

  diagnosis_id: z
    .string()
    .uuid("ID de diagnóstico inválido")
    .optional()
    .nullable(),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),
});

export type PrescriptionCreate = z.infer<typeof prescriptionCreateSchema>;
