/**
 * Zod validation schemas for odontogram forms.
 *
 * These mirror the backend Pydantic schemas for odontogram condition management.
 * All field names use snake_case to match the backend API.
 *
 * Key validation rules (from CLAUDE.md security spec):
 * - FDI tooth number: ^[1-8][1-8]$ (11–88 range, validated against known tooth sets)
 * - Notes fields are trimmed and null-normalized
 */

import { z } from "zod";

// ─── Condition Codes ───────────────────────────────────────────────────────────

/**
 * All supported dental condition codes.
 * Values match the backend OdontogramConditionCode enum exactly.
 */
export const CONDITION_CODES = [
  "caries",
  "restoration",
  "extraction",
  "absent",
  "crown",
  "endodontic",
  "implant",
  "fracture",
  "sealant",
  "fluorosis",
  "temporary",
  "prosthesis",
] as const;

export type ConditionCode = (typeof CONDITION_CODES)[number];

/** Spanish labels for condition codes — used in pickers, legends, and detail views. */
export const CONDITION_LABELS: Record<ConditionCode, string> = {
  caries: "Caries",
  restoration: "Restauración",
  extraction: "Extracción indicada",
  absent: "Ausente",
  crown: "Corona",
  endodontic: "Endodoncia",
  implant: "Implante",
  fracture: "Fractura",
  sealant: "Sellante",
  fluorosis: "Fluorosis",
  temporary: "Restauración temporal",
  prosthesis: "Prótesis",
};

/**
 * Default display colors per condition code (hex).
 * These are the frontend defaults — the backend catalog is the source of truth.
 * Used for rendering condition markers before the catalog is loaded.
 */
export const CONDITION_COLORS: Record<ConditionCode, string> = {
  caries: "#D32F2F",
  restoration: "#1565C0",
  extraction: "#424242",
  absent: "#9E9E9E",
  crown: "#F57C00",
  endodontic: "#6A1B9A",
  implant: "#00796B",
  fracture: "#E91E63",
  sealant: "#388E3C",
  fluorosis: "#FFB300",
  temporary: "#0097A7",
  prosthesis: "#512DA8",
};

// ─── Zones ────────────────────────────────────────────────────────────────────

/**
 * All possible tooth zones in FDI terminology.
 * Not all zones apply to every tooth — see getZonesForTooth() below.
 */
export const ZONES = [
  "mesial",
  "distal",
  "vestibular",
  "lingual",
  "palatino",
  "oclusal",
  "incisal",
  "root",
  "full",
] as const;

export type Zone = (typeof ZONES)[number];

/** Spanish labels for tooth zones — used in zone selectors and detail views. */
export const ZONE_LABELS: Record<Zone, string> = {
  mesial: "Mesial",
  distal: "Distal",
  vestibular: "Vestibular",
  lingual: "Lingual",
  palatino: "Palatino",
  oclusal: "Oclusal",
  incisal: "Incisal",
  root: "Raíz",
  full: "Completo",
};

// ─── Severities ───────────────────────────────────────────────────────────────

/** Severity levels — only applicable to conditions where severity_applicable is true. */
export const SEVERITIES = ["mild", "moderate", "severe"] as const;
export type Severity = (typeof SEVERITIES)[number];

/** Spanish labels for severity levels. */
export const SEVERITY_LABELS: Record<Severity, string> = {
  mild: "Leve",
  moderate: "Moderado",
  severe: "Severo",
};

// ─── Sources ──────────────────────────────────────────────────────────────────

/** How a condition was recorded — manual (doctor interaction) or voice (Voice-to-Odontogram). */
export const SOURCES = ["manual", "voice"] as const;
export type Source = (typeof SOURCES)[number];

// ─── Dentition Types ──────────────────────────────────────────────────────────

/** Dentition type determines which FDI tooth set is active for this patient. */
export const DENTITION_TYPES = ["adult", "pediatric", "mixed"] as const;
export type DentitionType = (typeof DENTITION_TYPES)[number];

/** Spanish labels for dentition types — used in the dentition toggle control. */
export const DENTITION_LABELS: Record<DentitionType, string> = {
  adult: "Adulto (permanente)",
  pediatric: "Pediátrico (temporal)",
  mixed: "Mixta",
};

// ─── FDI Tooth Sets ───────────────────────────────────────────────────────────

/**
 * All 32 permanent (adult) tooth numbers in FDI notation.
 * Quadrants: 1x (upper right), 2x (upper left), 3x (lower left), 4x (lower right).
 */
export const ADULT_TEETH: readonly number[] = [
  11, 12, 13, 14, 15, 16, 17, 18,
  21, 22, 23, 24, 25, 26, 27, 28,
  31, 32, 33, 34, 35, 36, 37, 38,
  41, 42, 43, 44, 45, 46, 47, 48,
];

/**
 * All 20 deciduous (pediatric) tooth numbers in FDI notation.
 * Quadrants: 5x (upper right), 6x (upper left), 7x (lower left), 8x (lower right).
 */
export const PEDIATRIC_TEETH: readonly number[] = [
  51, 52, 53, 54, 55,
  61, 62, 63, 64, 65,
  71, 72, 73, 74, 75,
  81, 82, 83, 84, 85,
];

/**
 * Set of anterior (front) tooth numbers — both adult and pediatric.
 * Anterior teeth use "incisal" instead of "oclusal" as the biting surface zone.
 * Stored as a Set for O(1) membership checks.
 */
export const ANTERIOR_TEETH: ReadonlySet<number> = new Set([
  // Adult anteriors
  11, 12, 13, 21, 22, 23,
  31, 32, 33, 41, 42, 43,
  // Pediatric anteriors
  51, 52, 53, 61, 62, 63,
  71, 72, 73, 81, 82, 83,
]);

// ─── Zone Helpers ─────────────────────────────────────────────────────────────

/**
 * Returns the applicable zones for a given tooth number.
 * Anterior teeth have an "incisal" surface; posterior teeth have "oclusal".
 *
 * @param toothNumber - FDI tooth number (e.g. 16, 21, 55)
 * @returns Array of applicable Zone values for the tooth
 *
 * @example
 * getZonesForTooth(11) // ["mesial", "distal", "vestibular", "lingual", "incisal", "root"]
 * getZonesForTooth(16) // ["mesial", "distal", "vestibular", "lingual", "oclusal", "root"]
 */
export function getZonesForTooth(toothNumber: number): Zone[] {
  if (ANTERIOR_TEETH.has(toothNumber)) {
    return ["mesial", "distal", "vestibular", "lingual", "incisal", "root"];
  }
  return ["mesial", "distal", "vestibular", "lingual", "oclusal", "root"];
}

/**
 * Returns true if the tooth number corresponds to an anterior (front) tooth.
 *
 * @param toothNumber - FDI tooth number
 */
export function isAnteriorTooth(toothNumber: number): boolean {
  return ANTERIOR_TEETH.has(toothNumber);
}

// ─── Condition Create Schema ──────────────────────────────────────────────────

/**
 * Schema for adding or updating a single condition on a tooth zone.
 * Mirrors the backend ConditionCreate Pydantic schema.
 */
export const conditionCreateSchema = z.object({
  tooth_number: z
    .number({ invalid_type_error: "El número de diente es requerido." })
    .int("El número de diente debe ser un entero.")
    .min(11, "Número de diente inválido (mín. 11).")
    .max(85, "Número de diente inválido (máx. 85)."),

  zone: z.enum(ZONES, {
    errorMap: () => ({ message: "Selecciona una zona válida." }),
  }),

  condition_code: z.enum(CONDITION_CODES, {
    errorMap: () => ({ message: "Selecciona una condición." }),
  }),

  severity: z
    .enum(SEVERITIES, {
      errorMap: () => ({ message: "Severidad inválida." }),
    })
    .optional()
    .nullable(),

  notes: z
    .string()
    .max(500, "Las notas no pueden exceder 500 caracteres.")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),

  source: z.enum(SOURCES).default("manual"),
});

export type ConditionCreateValues = z.infer<typeof conditionCreateSchema>;

// ─── Bulk Update Schema ───────────────────────────────────────────────────────

/**
 * Schema for bulk-applying multiple condition updates in a single API call.
 * Used when saving an entire examination session at once.
 * Backend enforces a max of 160 updates (one per zone across all 32 adult teeth).
 */
export const bulkUpdateSchema = z.object({
  updates: z
    .array(conditionCreateSchema)
    .min(1, "Debes incluir al menos una condición.")
    .max(160, "No puedes enviar más de 160 condiciones a la vez."),

  session_notes: z
    .string()
    .max(1000, "Las notas de sesión no pueden exceder 1000 caracteres.")
    .optional()
    .nullable(),
});

export type BulkUpdateValues = z.infer<typeof bulkUpdateSchema>;

// ─── Snapshot Create Schema ───────────────────────────────────────────────────

/**
 * Schema for creating a point-in-time odontogram snapshot.
 * Snapshots can optionally be linked to a clinical record or treatment plan.
 */
export const snapshotCreateSchema = z.object({
  label: z
    .string()
    .max(200, "La etiqueta no puede exceder 200 caracteres.")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),

  linked_record_id: z.string().uuid("ID de registro clínico inválido.").optional().nullable(),

  linked_treatment_plan_id: z
    .string()
    .uuid("ID de plan de tratamiento inválido.")
    .optional()
    .nullable(),
});

export type SnapshotCreateValues = z.infer<typeof snapshotCreateSchema>;

// ─── Dentition Toggle Schema ──────────────────────────────────────────────────

/**
 * Schema for switching a patient's active dentition type.
 * This is a destructive operation — the UI must show a confirmation dialog before submitting.
 */
export const dentitionToggleSchema = z.object({
  dentition_type: z.enum(DENTITION_TYPES, {
    errorMap: () => ({ message: "Tipo de dentición inválido." }),
  }),
});

export type DentitionToggleValues = z.infer<typeof dentitionToggleSchema>;
