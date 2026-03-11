/**
 * Zod validation schemas for orthodontics forms.
 *
 * These mirror the backend Pydantic schemas for orthodontic case management.
 * All field names use snake_case to match the backend API.
 *
 * Key validation rules (from CLAUDE.md security spec):
 * - FDI tooth number: integer 11–48 (orthodontics uses permanent dentition only)
 * - Money fields: integer cents >= 0 (never floats)
 */

import { z } from "zod";

// ─── Enums ────────────────────────────────────────────────────────────────────

export const APPLIANCE_TYPES = [
  "brackets",
  "aligners",
  "mixed",
] as const;

export const ANGLE_CLASSES = [
  "class_i",
  "class_ii_div1",
  "class_ii_div2",
  "class_iii",
] as const;

export const BRACKET_STATUSES = [
  "pending",
  "bonded",
  "removed",
  "not_applicable",
] as const;

export const BRACKET_TYPES = [
  "metalico",
  "ceramico",
  "autoligado",
  "lingual",
] as const;

export const PAYMENT_STATUSES = [
  "pending",
  "paid",
  "partial",
  "waived",
] as const;

// ─── Label Maps ───────────────────────────────────────────────────────────────

export const APPLIANCE_TYPE_LABELS: Record<string, string> = {
  brackets: "Brackets",
  aligners: "Alineadores",
  mixed: "Mixto",
};

export const ANGLE_CLASS_LABELS: Record<string, string> = {
  class_i: "Clase I",
  class_ii_div1: "Clase II Div 1",
  class_ii_div2: "Clase II Div 2",
  class_iii: "Clase III",
};

export const BRACKET_STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  bonded: "Cementado",
  removed: "Removido",
  not_applicable: "No aplica",
};

export const BRACKET_TYPE_LABELS: Record<string, string> = {
  metalico: "Metálico",
  ceramico: "Cerámico",
  autoligado: "Autoligado",
  lingual: "Lingual",
};

export const ORTHO_STATUS_LABELS: Record<string, string> = {
  planning: "Planificación",
  bonding: "Cementado",
  active_treatment: "Tratamiento activo",
  retention: "Retención",
  completed: "Completado",
  cancelled: "Cancelado",
};

// ─── Ortho Case Schemas ───────────────────────────────────────────────────────

/**
 * Schema for creating a new orthodontic case.
 * Mirrors the backend OrthoCaseCreate Pydantic schema.
 */
export const orthoCaseCreateSchema = z.object({
  appliance_type: z
    .enum(APPLIANCE_TYPES, {
      errorMap: () => ({ message: "Tipo de aparato inválido" }),
    }),

  angle_class: z
    .enum(ANGLE_CLASSES, {
      errorMap: () => ({ message: "Clase de Angle inválida" }),
    })
    .optional()
    .nullable(),

  malocclusion_type: z
    .string()
    .max(200, "El tipo de maloclusión no puede exceder 200 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  treatment_plan_id: z
    .string()
    .uuid("ID de plan de tratamiento inválido")
    .optional()
    .nullable(),

  estimated_duration_months: z
    .number({ invalid_type_error: "La duración estimada debe ser un número" })
    .int("La duración debe ser un número entero")
    .min(1, "La duración mínima es 1 mes")
    .max(120, "La duración máxima es 120 meses")
    .optional()
    .nullable(),

  total_cost_estimated: z
    .number({ invalid_type_error: "El costo estimado debe ser un número" })
    .int("El costo debe ser un número entero en centavos")
    .min(0, "El costo estimado no puede ser negativo")
    .optional(),

  initial_payment: z
    .number({ invalid_type_error: "El pago inicial debe ser un número" })
    .int("El pago debe ser un número entero en centavos")
    .min(0, "El pago inicial no puede ser negativo")
    .optional(),

  monthly_payment: z
    .number({ invalid_type_error: "El pago mensual debe ser un número" })
    .int("El pago debe ser un número entero en centavos")
    .min(0, "El pago mensual no puede ser negativo")
    .optional(),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),
});

export type OrthoCaseCreateForm = z.infer<typeof orthoCaseCreateSchema>;

/**
 * Schema for updating an existing orthodontic case.
 * All fields are optional.
 */
export const orthoCaseUpdateSchema = z.object({
  appliance_type: z
    .enum(APPLIANCE_TYPES, {
      errorMap: () => ({ message: "Tipo de aparato inválido" }),
    })
    .optional(),

  angle_class: z
    .enum(ANGLE_CLASSES, {
      errorMap: () => ({ message: "Clase de Angle inválida" }),
    })
    .optional()
    .nullable(),

  malocclusion_type: z
    .string()
    .max(200, "El tipo de maloclusión no puede exceder 200 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  treatment_plan_id: z
    .string()
    .uuid("ID de plan de tratamiento inválido")
    .optional()
    .nullable(),

  estimated_duration_months: z
    .number({ invalid_type_error: "La duración estimada debe ser un número" })
    .int("La duración debe ser un número entero")
    .min(1, "La duración mínima es 1 mes")
    .max(120, "La duración máxima es 120 meses")
    .optional()
    .nullable(),

  total_cost_estimated: z
    .number({ invalid_type_error: "El costo estimado debe ser un número" })
    .int("El costo debe ser un número entero en centavos")
    .min(0, "El costo estimado no puede ser negativo")
    .optional(),

  initial_payment: z
    .number({ invalid_type_error: "El pago inicial debe ser un número" })
    .int("El pago debe ser un número entero en centavos")
    .min(0, "El pago inicial no puede ser negativo")
    .optional(),

  monthly_payment: z
    .number({ invalid_type_error: "El pago mensual debe ser un número" })
    .int("El pago debe ser un número entero en centavos")
    .min(0, "El pago mensual no puede ser negativo")
    .optional(),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),
});

export type OrthoCaseUpdateForm = z.infer<typeof orthoCaseUpdateSchema>;

// ─── Visit Schemas ────────────────────────────────────────────────────────────

/**
 * Schema for creating a new orthodontic visit.
 * Mirrors the backend OrthoVisitCreate Pydantic schema.
 */
export const orthoVisitCreateSchema = z.object({
  visit_date: z
    .string()
    .min(1, "La fecha de visita es requerida")
    .regex(
      /^\d{4}-\d{2}-\d{2}$/,
      "La fecha debe tener el formato YYYY-MM-DD",
    ),

  wire_upper: z
    .string()
    .max(100, "La descripción del arco superior no puede exceder 100 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  wire_lower: z
    .string()
    .max(100, "La descripción del arco inferior no puede exceder 100 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  elastics: z
    .string()
    .max(200, "La descripción de los elásticos no puede exceder 200 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  adjustments: z
    .string()
    .max(1000, "La descripción de ajustes no puede exceder 1000 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  next_visit_date: z
    .string()
    .regex(
      /^\d{4}-\d{2}-\d{2}$/,
      "La fecha de próxima visita debe tener el formato YYYY-MM-DD",
    )
    .optional()
    .nullable(),

  payment_amount: z
    .number({ invalid_type_error: "El monto del pago debe ser un número" })
    .int("El monto debe ser un número entero en centavos")
    .min(0, "El monto del pago no puede ser negativo")
    .optional(),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),
});

export type OrthoVisitCreateForm = z.infer<typeof orthoVisitCreateSchema>;

/**
 * Schema for updating an existing orthodontic visit.
 * All fields are optional.
 */
export const orthoVisitUpdateSchema = z.object({
  wire_upper: z
    .string()
    .max(100, "La descripción del arco superior no puede exceder 100 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  wire_lower: z
    .string()
    .max(100, "La descripción del arco inferior no puede exceder 100 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  elastics: z
    .string()
    .max(200, "La descripción de los elásticos no puede exceder 200 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  adjustments: z
    .string()
    .max(1000, "La descripción de ajustes no puede exceder 1000 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  next_visit_date: z
    .string()
    .regex(
      /^\d{4}-\d{2}-\d{2}$/,
      "La fecha de próxima visita debe tener el formato YYYY-MM-DD",
    )
    .optional()
    .nullable(),

  payment_status: z
    .enum(PAYMENT_STATUSES, {
      errorMap: () => ({ message: "Estado de pago inválido" }),
    })
    .optional()
    .nullable(),

  payment_amount: z
    .number({ invalid_type_error: "El monto del pago debe ser un número" })
    .int("El monto debe ser un número entero en centavos")
    .min(0, "El monto del pago no puede ser negativo")
    .optional()
    .nullable(),
});

export type OrthoVisitUpdateForm = z.infer<typeof orthoVisitUpdateSchema>;

// ─── Bonding Schemas ──────────────────────────────────────────────────────────

/**
 * Schema for a single tooth entry in a bonding record.
 * FDI range 11-48 covers the full permanent dentition used in orthodontics.
 */
export const bondingToothSchema = z.object({
  tooth_number: z
    .number({ invalid_type_error: "El número de diente debe ser un número" })
    .int("El número de diente debe ser un entero")
    .min(11, "Número de diente inválido (mín. 11)")
    .max(48, "Número de diente inválido (máx. 48)"),

  bracket_status: z
    .enum(BRACKET_STATUSES, {
      errorMap: () => ({ message: "Estado de bracket inválido" }),
    }),

  bracket_type: z
    .enum(BRACKET_TYPES, {
      errorMap: () => ({ message: "Tipo de bracket inválido" }),
    })
    .optional()
    .nullable(),

  slot_size: z
    .string()
    .max(20, "El tamaño de slot no puede exceder 20 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  wire_type: z
    .string()
    .max(100, "El tipo de arco no puede exceder 100 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  band: z
    .boolean()
    .optional(),

  notes: z
    .string()
    .max(500, "Las notas no pueden exceder 500 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),
});

export type BondingToothForm = z.infer<typeof bondingToothSchema>;

/**
 * Schema for creating a bonding record with one or more teeth.
 * Mirrors the backend BondingRecordCreate Pydantic schema.
 */
export const bondingRecordCreateSchema = z.object({
  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),

  teeth: z
    .array(bondingToothSchema)
    .min(1, "Debes registrar al menos un diente")
    .max(32, "No puedes registrar más de 32 dientes"),
});

export type BondingRecordCreateForm = z.infer<typeof bondingRecordCreateSchema>;

// ─── Material Schema ──────────────────────────────────────────────────────────

/**
 * Schema for recording a material used in an orthodontic case.
 * Mirrors the backend MaterialCreate Pydantic schema.
 */
export const materialCreateSchema = z.object({
  inventory_item_id: z
    .string()
    .uuid("ID de ítem de inventario inválido"),

  visit_id: z
    .string()
    .uuid("ID de visita inválido")
    .optional()
    .nullable(),

  quantity_used: z
    .number({ invalid_type_error: "La cantidad debe ser un número" })
    .positive("La cantidad debe ser mayor a 0"),

  notes: z
    .string()
    .max(500, "Las notas no pueden exceder 500 caracteres")
    .transform((v) => v.trim())
    .optional()
    .nullable(),
});

export type MaterialCreateForm = z.infer<typeof materialCreateSchema>;
