/**
 * Zod validation schemas for procedure forms.
 *
 * These mirror the backend Pydantic schemas for clinical procedure creation.
 * All field names use snake_case to match the backend API.
 *
 * Key validation rules (from CLAUDE.md security spec):
 * - CUPS code: ^[0-9]{6}$ (6 digits)
 * - FDI tooth number: integer 11–85
 */

import { z } from "zod";

// ─── Material Schema ──────────────────────────────────────────────────────────

/**
 * Schema for a single material used during a procedure.
 */
export const procedureMaterialSchema = z.object({
  name: z
    .string()
    .min(1, "El nombre del material es requerido")
    .max(200, "El nombre del material no puede exceder 200 caracteres")
    .transform((v) => v.trim()),
  quantity: z
    .number({ invalid_type_error: "La cantidad debe ser un número" })
    .positive("La cantidad debe ser mayor a 0")
    .optional(),
});

export type ProcedureMaterial = z.infer<typeof procedureMaterialSchema>;

// ─── Procedure Create Schema ──────────────────────────────────────────────────

/**
 * Schema for creating a new clinical procedure record.
 * Mirrors the backend ProcedureCreate Pydantic schema.
 */
export const procedureCreateSchema = z.object({
  cups_code: z
    .string()
    .min(1, "El código CUPS es requerido")
    .regex(/^[0-9]{6}$/, "Código CUPS inválido (debe tener exactamente 6 dígitos)")
    .transform((v) => v.trim()),

  cups_description: z
    .string()
    .min(1, "La descripción del procedimiento es requerida")
    .max(500, "La descripción no puede exceder 500 caracteres")
    .transform((v) => v.trim()),

  tooth_number: z
    .number({ invalid_type_error: "El número de diente debe ser un número" })
    .int("El número de diente debe ser un entero")
    .min(11, "Número de diente inválido (mín. 11)")
    .max(85, "Número de diente inválido (máx. 85)")
    .optional()
    .nullable(),

  zones: z
    .array(z.string().min(1).max(50))
    .max(10, "No puedes seleccionar más de 10 zonas")
    .optional()
    .nullable(),

  materials_used: z
    .array(procedureMaterialSchema)
    .max(50, "No puedes registrar más de 50 materiales")
    .optional()
    .nullable(),

  treatment_plan_item_id: z
    .string()
    .uuid("ID de ítem de plan de tratamiento inválido")
    .optional()
    .nullable(),

  clinical_record_id: z
    .string()
    .uuid("ID de registro clínico inválido")
    .optional()
    .nullable(),

  duration_minutes: z
    .number({ invalid_type_error: "La duración debe ser un número" })
    .int("La duración debe ser un número entero")
    .min(1, "La duración mínima es 1 minuto")
    .max(480, "La duración máxima es 480 minutos (8 horas)")
    .optional()
    .nullable(),
});

export type ProcedureCreate = z.infer<typeof procedureCreateSchema>;
