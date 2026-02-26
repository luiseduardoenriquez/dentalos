/**
 * Zod validation schemas for payment plan forms.
 * Mirrors the backend PaymentPlanCreate Pydantic schema.
 * All field names use snake_case to match the backend API.
 */

import { z } from "zod";

// ─── Frequency ───────────────────────────────────────────────────────────────

export const PAYMENT_PLAN_FREQUENCIES = ["weekly", "biweekly", "monthly"] as const;
export type PaymentPlanFrequency = (typeof PAYMENT_PLAN_FREQUENCIES)[number];

export const FREQUENCY_LABELS: Record<PaymentPlanFrequency, string> = {
  weekly: "Semanal",
  biweekly: "Quincenal",
  monthly: "Mensual",
};

// ─── Payment Plan Create Schema ──────────────────────────────────────────────

export const paymentPlanCreateSchema = z.object({
  num_installments: z.coerce
    .number({ invalid_type_error: "Ingresa un número válido" })
    .int("Debe ser un número entero")
    .min(2, "Mínimo 2 cuotas")
    .max(48, "Máximo 48 cuotas"),

  first_due_date: z
    .string()
    .min(1, "Fecha de inicio requerida")
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido"),
});

export type PaymentPlanCreateFormValues = z.infer<typeof paymentPlanCreateSchema>;
