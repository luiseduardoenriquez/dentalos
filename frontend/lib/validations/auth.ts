/**
 * Zod validation schemas for authentication forms.
 *
 * These mirror the backend Pydantic schemas in app/schemas/auth.py.
 * Validation rules must stay in sync with the backend.
 */

import { z } from "zod";

// ─── Shared Validators ────────────────────────────────────────────────────────

/**
 * Password strength rules — mirrors backend _validate_password_strength().
 * Min 8 chars, at least one uppercase, one lowercase, one digit.
 */
const passwordSchema = z
  .string()
  .min(8, "La contraseña debe tener al menos 8 caracteres")
  .max(128, "La contraseña no puede exceder 128 caracteres")
  .refine((v) => /[A-Z]/.test(v), "La contraseña debe tener al menos una letra mayúscula")
  .refine((v) => /[a-z]/.test(v), "La contraseña debe tener al menos una letra minúscula")
  .refine((v) => /[0-9]/.test(v), "La contraseña debe tener al menos un número");

/** LATAM phone regex — mirrors backend pattern `^\+?[0-9]{7,15}$` */
const phoneSchema = z
  .string()
  .regex(/^\+?[0-9]{7,15}$/, "Número de teléfono inválido (ej: +573001234567)")
  .optional()
  .or(z.literal(""))
  .transform((v) => (v === "" ? undefined : v));

// ─── Login ────────────────────────────────────────────────────────────────────

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "El correo electrónico es requerido")
    .email("Ingresa un correo electrónico válido")
    .transform((v) => v.trim().toLowerCase()),
  password: z.string().min(1, "La contraseña es requerida"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

// ─── Register ─────────────────────────────────────────────────────────────────

/**
 * Supported countries (matches backend enum in RegisterRequest).
 */
export const SUPPORTED_COUNTRIES = ["CO", "MX", "CL", "AR", "PE", "EC"] as const;
export type SupportedCountry = (typeof SUPPORTED_COUNTRIES)[number];

export const COUNTRY_LABELS: Record<SupportedCountry, string> = {
  CO: "Colombia",
  MX: "México",
  CL: "Chile",
  AR: "Argentina",
  PE: "Perú",
  EC: "Ecuador",
};

export const registerSchema = z.object({
  name: z
    .string()
    .min(1, "El nombre es requerido")
    .max(200, "El nombre no puede exceder 200 caracteres")
    .transform((v) => v.trim()),
  clinic_name: z
    .string()
    .min(1, "El nombre de la clínica es requerido")
    .max(200, "El nombre no puede exceder 200 caracteres")
    .transform((v) => v.trim()),
  email: z
    .string()
    .min(1, "El correo electrónico es requerido")
    .email("Ingresa un correo electrónico válido")
    .transform((v) => v.trim().toLowerCase()),
  password: passwordSchema,
  country: z.enum(SUPPORTED_COUNTRIES, {
    errorMap: () => ({ message: "Selecciona un país válido" }),
  }),
  phone: phoneSchema,
});

export type RegisterFormValues = z.infer<typeof registerSchema>;

// ─── Forgot Password ──────────────────────────────────────────────────────────

export const forgotPasswordSchema = z.object({
  email: z
    .string()
    .min(1, "El correo electrónico es requerido")
    .email("Ingresa un correo electrónico válido")
    .transform((v) => v.trim().toLowerCase()),
});

export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

// ─── Reset Password ───────────────────────────────────────────────────────────

export const resetPasswordSchema = z
  .object({
    token: z.string().min(1, "Token inválido"),
    new_password: passwordSchema,
    confirm_password: z.string().min(1, "Confirma tu contraseña"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Las contraseñas no coinciden",
    path: ["confirm_password"],
  });

export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

// ─── Change Password ──────────────────────────────────────────────────────────

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "La contraseña actual es requerida"),
    new_password: passwordSchema,
    confirm_password: z.string().min(1, "Confirma tu nueva contraseña"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Las contraseñas no coinciden",
    path: ["confirm_password"],
  })
  .refine((data) => data.new_password !== data.current_password, {
    message: "La nueva contraseña debe ser diferente a la actual",
    path: ["new_password"],
  });

export type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>;

// ─── Accept Invite ────────────────────────────────────────────────────────────

export const acceptInviteSchema = z
  .object({
    token: z.string().min(1, "Token de invitación inválido"),
    name: z
      .string()
      .min(1, "El nombre es requerido")
      .max(200, "El nombre no puede exceder 200 caracteres")
      .transform((v) => v.trim()),
    password: passwordSchema,
    confirm_password: z.string().min(1, "Confirma tu contraseña"),
    phone: phoneSchema,
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Las contraseñas no coinciden",
    path: ["confirm_password"],
  });

export type AcceptInviteFormValues = z.infer<typeof acceptInviteSchema>;
