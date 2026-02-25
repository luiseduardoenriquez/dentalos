/**
 * Zod validation schemas for patient forms.
 *
 * These mirror the backend Pydantic schemas for patient creation/update.
 * All field names use snake_case to match the backend API.
 *
 * Key validation rules (from CLAUDE.md security spec):
 * - Colombian cedula (CC): ^[0-9]{6,12}$
 * - Phone (LATAM): ^\+?[0-9]{7,15}$
 */

import { z } from "zod";

// ─── Document Types ───────────────────────────────────────────────────────────

/**
 * Colombian and LATAM identity document types.
 * CC: Cédula de Ciudadanía (Colombia)
 * CE: Cédula de Extranjería
 * PA: Pasaporte
 * PEP: Permiso Especial de Permanencia (Venezuela)
 * TI: Tarjeta de Identidad (minors)
 */
export const DOCUMENT_TYPES = ["CC", "CE", "PA", "PEP", "TI"] as const;
export type DocumentType = (typeof DOCUMENT_TYPES)[number];

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  CC: "Cédula de Ciudadanía",
  CE: "Cédula de Extranjería",
  PA: "Pasaporte",
  PEP: "Permiso Especial de Permanencia",
  TI: "Tarjeta de Identidad",
};

// ─── Gender ───────────────────────────────────────────────────────────────────

export const GENDERS = ["male", "female", "other"] as const;
export type Gender = (typeof GENDERS)[number];

export const GENDER_LABELS: Record<Gender, string> = {
  male: "Masculino",
  female: "Femenino",
  other: "Otro",
};

// ─── Blood Types ──────────────────────────────────────────────────────────────

export const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] as const;
export type BloodType = (typeof BLOOD_TYPES)[number];

// ─── Referral Sources ─────────────────────────────────────────────────────────

export const REFERRAL_SOURCES = [
  "instagram",
  "facebook",
  "google",
  "referido",
  "calle",
  "otro",
] as const;
export type ReferralSource = (typeof REFERRAL_SOURCES)[number];

export const REFERRAL_SOURCE_LABELS: Record<ReferralSource, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  google: "Google",
  referido: "Referido de paciente",
  calle: "Pasando por la calle",
  otro: "Otro",
};

// ─── Shared Validators ────────────────────────────────────────────────────────

/** LATAM phone validator — mirrors backend pattern */
const phoneFieldSchema = z
  .string()
  .regex(/^\+?[0-9]{7,15}$/, "Teléfono inválido (ej: +573001234567 o 3001234567)")
  .optional()
  .or(z.literal(""))
  .transform((v) => (v === "" ? undefined : v));

/** YYYY-MM-DD date validator (no future dates for birthdate) */
const birthdateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido (YYYY-MM-DD)")
  .refine((v) => {
    const date = new Date(v);
    return !isNaN(date.getTime()) && date <= new Date();
  }, "La fecha de nacimiento no puede ser en el futuro")
  .optional()
  .or(z.literal(""))
  .transform((v) => (v === "" ? undefined : v));

/**
 * Document number validator that adapts rules per document type.
 * Used with superRefine for cross-field validation.
 */
function validateDocumentNumber(document_type: string, document_number: string): string | null {
  const trimmed = document_number.trim();
  if (!trimmed) return "El número de documento es requerido";

  switch (document_type) {
    case "CC":
      // Colombian cedula: 6-12 digits
      if (!/^[0-9]{6,12}$/.test(trimmed)) {
        return "La cédula debe tener entre 6 y 12 dígitos";
      }
      break;
    case "TI":
      // Tarjeta de identidad: 10-11 digits
      if (!/^[0-9]{10,11}$/.test(trimmed)) {
        return "La tarjeta de identidad debe tener entre 10 y 11 dígitos";
      }
      break;
    case "CE":
      // Cédula extranjería: alphanumeric, 4-12 chars
      if (!/^[a-zA-Z0-9]{4,12}$/.test(trimmed)) {
        return "La cédula de extranjería debe tener entre 4 y 12 caracteres alfanuméricos";
      }
      break;
    case "PA":
      // Passport: alphanumeric, 6-20 chars
      if (!/^[a-zA-Z0-9]{6,20}$/.test(trimmed)) {
        return "El pasaporte debe tener entre 6 y 20 caracteres alfanuméricos";
      }
      break;
    case "PEP":
      // PEP: alphanumeric, 4-20 chars
      if (!/^[a-zA-Z0-9]{4,20}$/.test(trimmed)) {
        return "El PEP debe tener entre 4 y 20 caracteres alfanuméricos";
      }
      break;
    default:
      if (trimmed.length < 4 || trimmed.length > 20) {
        return "Número de documento inválido";
      }
  }

  return null; // valid
}

// ─── Patient Create Schema ────────────────────────────────────────────────────

export const patientCreateSchema = z
  .object({
    // Identity
    document_type: z.enum(DOCUMENT_TYPES, {
      errorMap: () => ({ message: "Selecciona un tipo de documento" }),
    }),
    document_number: z
      .string()
      .min(1, "El número de documento es requerido")
      .max(20, "Número de documento demasiado largo")
      .transform((v) => v.trim()),

    // Personal info
    first_name: z
      .string()
      .min(1, "El nombre es requerido")
      .max(100, "El nombre no puede exceder 100 caracteres")
      .transform((v) => v.trim()),
    last_name: z
      .string()
      .min(1, "El apellido es requerido")
      .max(100, "El apellido no puede exceder 100 caracteres")
      .transform((v) => v.trim()),
    birthdate: birthdateSchema,
    gender: z
      .enum(GENDERS, {
        errorMap: () => ({ message: "Selecciona un género" }),
      })
      .optional(),
    blood_type: z
      .enum(BLOOD_TYPES, {
        errorMap: () => ({ message: "Tipo de sangre inválido" }),
      })
      .optional(),

    // Contact
    phone: phoneFieldSchema,
    phone_secondary: phoneFieldSchema,
    email: z
      .string()
      .email("Ingresa un correo electrónico válido")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.toLowerCase())),
    address: z
      .string()
      .max(200, "La dirección no puede exceder 200 caracteres")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.trim())),
    city: z
      .string()
      .max(100, "La ciudad no puede exceder 100 caracteres")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.trim())),
    state_province: z
      .string()
      .max(100, "El departamento no puede exceder 100 caracteres")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.trim())),

    // Emergency contact
    emergency_contact_name: z
      .string()
      .max(200, "El nombre no puede exceder 200 caracteres")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.trim())),
    emergency_contact_phone: phoneFieldSchema,

    // Insurance
    insurance_provider: z
      .string()
      .max(200, "El nombre no puede exceder 200 caracteres")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.trim())),
    insurance_policy_number: z
      .string()
      .max(50, "El número de póliza no puede exceder 50 caracteres")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.trim())),

    // Medical history
    allergies: z.array(z.string().min(1).max(100)).optional().default([]),
    chronic_conditions: z.array(z.string().min(1).max(100)).optional().default([]),

    // Administrative
    referral_source: z
      .enum(REFERRAL_SOURCES, {
        errorMap: () => ({ message: "Fuente de referido inválida" }),
      })
      .optional(),
    notes: z
      .string()
      .max(2000, "Las notas no pueden exceder 2000 caracteres")
      .optional()
      .or(z.literal(""))
      .transform((v) => (v === "" ? undefined : v?.trim())),
  })
  .superRefine((data, ctx) => {
    // Cross-field document number validation
    const error = validateDocumentNumber(data.document_type, data.document_number);
    if (error) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: error,
        path: ["document_number"],
      });
    }
  });

export type PatientCreateFormValues = z.infer<typeof patientCreateSchema>;

// ─── Patient Update Schema ────────────────────────────────────────────────────

/**
 * All fields optional for partial updates.
 * Backend uses PUT (not PATCH) for MVP, but we still send only changed fields.
 */
export const patientUpdateSchema = patientCreateSchema.partial().extend({
  // document_type and document_number remain required when updating identity,
  // but they can be omitted entirely for non-identity updates.
  document_type: z
    .enum(DOCUMENT_TYPES, {
      errorMap: () => ({ message: "Selecciona un tipo de documento" }),
    })
    .optional(),
  document_number: z
    .string()
    .max(20, "Número de documento demasiado largo")
    .optional()
    .transform((v) => v?.trim()),
});

export type PatientUpdateFormValues = z.infer<typeof patientUpdateSchema>;

// ─── Patient Search Schema ────────────────────────────────────────────────────

export const patientSearchSchema = z.object({
  q: z
    .string()
    .min(2, "Ingresa al menos 2 caracteres para buscar")
    .max(100, "La búsqueda es demasiado larga")
    .transform((v) => v.trim()),
});

export type PatientSearchFormValues = z.infer<typeof patientSearchSchema>;
