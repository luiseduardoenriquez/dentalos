/**
 * Zod validation schemas for invoice forms.
 * Mirrors the backend InvoiceCreate Pydantic schema.
 * All field names use snake_case to match the backend API.
 */

import { z } from "zod";

// ─── Invoice Item Schema ─────────────────────────────────────────────────────

export const invoiceItemSchema = z.object({
  description: z
    .string()
    .trim()
    .min(1, "Descripción requerida")
    .max(500, "La descripción no puede exceder 500 caracteres"),

  service_id: z.string().uuid().optional().nullable(),

  cups_code: z
    .string()
    .regex(/^[0-9]{6}$/, "Código CUPS debe ser 6 dígitos")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),

  quantity: z.coerce
    .number({ invalid_type_error: "Ingresa una cantidad válida" })
    .int("La cantidad debe ser un número entero")
    .min(1, "Mínimo 1"),

  unit_price_display: z
    .string()
    .min(1, "Precio requerido")
    .regex(/^[0-9]+$/, "Solo números")
    .transform((v) => parseInt(v, 10) * 100),

  discount_display: z
    .string()
    .regex(/^[0-9]*$/, "Solo números")
    .optional()
    .default("0")
    .transform((v) => (v ? parseInt(v, 10) * 100 : 0)),

  tooth_number: z
    .string()
    .optional()
    .nullable()
    .transform((v) => (v ? parseInt(v, 10) : null))
    .refine((v) => v === null || (v >= 11 && v <= 88), {
      message: "Número de diente inválido (11–88)",
    }),
});

export type InvoiceItemFormValues = z.infer<typeof invoiceItemSchema>;

// ─── Invoice Create Schema ───────────────────────────────────────────────────

export const invoiceCreateSchema = z.object({
  quotation_id: z.string().uuid().optional().nullable(),

  due_date: z
    .string()
    .min(1, "Fecha de vencimiento requerida")
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Formato de fecha inválido"),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .optional()
    .nullable()
    .transform((v) => v?.trim() || null),

  items: z
    .array(invoiceItemSchema)
    .min(1, "Agregue al menos un ítem a la factura"),
});

export type InvoiceCreateFormValues = z.infer<typeof invoiceCreateSchema>;
