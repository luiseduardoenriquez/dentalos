/**
 * Zod validation schemas for diagnosis forms.
 *
 * These mirror the backend Pydantic schemas for diagnosis creation/update.
 * All field names use snake_case to match the backend API.
 *
 * Key validation rules (from CLAUDE.md security spec):
 * - CIE-10 code: ^[A-Z][0-9]{2}(\.[0-9]{1,4})?$
 * - FDI tooth number: integer 11–85
 */

import { z } from "zod";

// ─── Severity ─────────────────────────────────────────────────────────────────

export const SEVERITY_OPTIONS = ["mild", "moderate", "severe"] as const;
export type Severity = (typeof SEVERITY_OPTIONS)[number];

export const SEVERITY_LABELS: Record<Severity, string> = {
  mild: "Leve",
  moderate: "Moderado",
  severe: "Severo",
};

// ─── Diagnosis Status ─────────────────────────────────────────────────────────

export const DIAGNOSIS_STATUS_OPTIONS = ["active", "resolved", "chronic"] as const;
export type DiagnosisStatus = (typeof DIAGNOSIS_STATUS_OPTIONS)[number];

export const DIAGNOSIS_STATUS_LABELS: Record<DiagnosisStatus, string> = {
  active: "Activo",
  resolved: "Resuelto",
  chronic: "Crónico",
};

// ─── Diagnosis Create Schema ──────────────────────────────────────────────────

/**
 * Schema for creating a new diagnosis.
 * Mirrors the backend DiagnosisCreate Pydantic schema.
 */
export const diagnosisCreateSchema = z.object({
  cie10_code: z
    .string()
    .min(1, "El código CIE-10 es requerido")
    .regex(
      /^[A-Z][0-9]{2}(\.[0-9]{1,4})?$/,
      "Código CIE-10 inválido (ej: K02.1 o A09)",
    )
    .transform((v) => v.trim().toUpperCase()),

  cie10_description: z
    .string()
    .min(1, "La descripción del diagnóstico es requerida")
    .max(500, "La descripción no puede exceder 500 caracteres")
    .transform((v) => v.trim()),

  severity: z.enum(SEVERITY_OPTIONS, {
    errorMap: () => ({ message: "Selecciona la severidad del diagnóstico" }),
  }),

  tooth_number: z
    .number({ invalid_type_error: "El número de diente debe ser un número" })
    .int("El número de diente debe ser un entero")
    .min(11, "Número de diente inválido (mín. 11)")
    .max(85, "Número de diente inválido (máx. 85)")
    .optional()
    .nullable(),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),
});

export type DiagnosisCreate = z.infer<typeof diagnosisCreateSchema>;

// ─── Diagnosis Update Schema ──────────────────────────────────────────────────

/**
 * Schema for updating an existing diagnosis.
 * All fields are optional — only send what changed.
 */
export const diagnosisUpdateSchema = z.object({
  severity: z
    .enum(SEVERITY_OPTIONS, {
      errorMap: () => ({ message: "Severidad inválida" }),
    })
    .optional(),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .optional()
    .nullable()
    .transform((v) => (v === "" ? null : v?.trim() ?? null)),

  status: z
    .enum(DIAGNOSIS_STATUS_OPTIONS, {
      errorMap: () => ({ message: "Estado inválido" }),
    })
    .optional(),
});

export type DiagnosisUpdate = z.infer<typeof diagnosisUpdateSchema>;
