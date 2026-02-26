/**
 * Zod validation schemas for payment forms.
 * Mirrors the backend PaymentCreate Pydantic schema.
 * All field names use snake_case to match the backend API.
 */

import { z } from "zod";

// ─── Payment Method ──────────────────────────────────────────────────────────

export const PAYMENT_METHODS = ["cash", "card", "transfer", "other"] as const;
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: "Efectivo",
  card: "Tarjeta",
  transfer: "Transferencia",
  other: "Otro",
};

// ─── Payment Record Schema ───────────────────────────────────────────────────

export const paymentRecordSchema = z.object({
  amount_display: z
    .string()
    .min(1, "Monto requerido")
    .regex(/^[0-9]+$/, "Solo números")
    .transform((v) => parseInt(v, 10) * 100),

  payment_method: z.enum(PAYMENT_METHODS, {
    errorMap: () => ({ message: "Selecciona un método de pago" }),
  }),

  reference_number: z
    .string()
    .max(100, "La referencia no puede exceder 100 caracteres")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),

  notes: z
    .string()
    .max(1000, "Las notas no pueden exceder 1000 caracteres")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),
});

export type PaymentRecordFormValues = z.infer<typeof paymentRecordSchema>;
