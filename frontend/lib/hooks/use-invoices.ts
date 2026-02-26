"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface InvoiceItemResponse {
  id: string;
  invoice_id: string;
  service_id: string | null;
  description: string;
  cups_code: string | null;
  quantity: number;
  unit_price: number; // cents
  discount: number; // cents
  line_total: number; // cents
  sort_order: number;
  tooth_number: number | null;
  created_at: string;
  updated_at: string;
}

export interface InvoiceResponse {
  id: string;
  invoice_number: string;
  patient_id: string;
  created_by: string;
  quotation_id: string | null;
  subtotal: number; // cents
  tax: number; // cents
  total: number; // cents
  amount_paid: number; // cents
  balance: number; // cents
  status: "draft" | "sent" | "partial" | "paid" | "overdue" | "cancelled";
  due_date: string | null;
  paid_at: string | null;
  notes: string | null;
  items: InvoiceItemResponse[];
  days_until_due: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InvoiceListResponse {
  items: InvoiceResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface InvoiceItemCreate {
  description: string;
  cups_code?: string | null;
  service_id?: string | null;
  quantity: number;
  unit_price: number; // cents
  discount?: number; // cents
  tooth_number?: number | null;
}

export interface InvoiceCreate {
  quotation_id?: string | null;
  items?: InvoiceItemCreate[];
  due_date?: string | null;
  notes?: string | null;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const INVOICES_QUERY_KEY = ["invoices"] as const;

export const invoicesQueryKey = (
  patientId: string,
  page: number,
  pageSize: number,
) => ["invoices", patientId, page, pageSize] as const;

export const invoiceQueryKey = (
  patientId: string,
  invoiceId: string,
) => ["invoices", patientId, invoiceId] as const;

// ─── useInvoices ──────────────────────────────────────────────────────────────

/**
 * Paginated list of invoices for a patient.
 */
export function useInvoices(
  patientId: string,
  page: number,
  pageSize: number,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: invoicesQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<InvoiceListResponse>(
        `/patients/${patientId}/invoices${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useInvoice ───────────────────────────────────────────────────────────────

/**
 * Single invoice by ID.
 */
export function useInvoice(patientId: string, invoiceId: string) {
  return useQuery({
    queryKey: invoiceQueryKey(patientId, invoiceId),
    queryFn: () =>
      apiGet<InvoiceResponse>(
        `/patients/${patientId}/invoices/${invoiceId}`,
      ),
    enabled: Boolean(patientId) && Boolean(invoiceId),
    staleTime: 60_000,
  });
}

// ─── useCreateInvoice ─────────────────────────────────────────────────────────

/**
 * POST /patients/{id}/invoices — creates a new invoice.
 */
export function useCreateInvoice(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: InvoiceCreate) =>
      apiPost<InvoiceResponse>(`/patients/${patientId}/invoices`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices", patientId] });
      success("Factura creada", "La factura fue generada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear la factura. Inténtalo de nuevo.";
      error("Error al crear factura", message);
    },
  });
}

// ─── useCancelInvoice ─────────────────────────────────────────────────────────

/**
 * POST /patients/{id}/invoices/{invoiceId}/cancel — cancels an invoice.
 */
export function useCancelInvoice(patientId: string, invoiceId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () =>
      apiPost<InvoiceResponse>(
        `/patients/${patientId}/invoices/${invoiceId}/cancel`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceQueryKey(patientId, invoiceId),
      });
      queryClient.invalidateQueries({ queryKey: ["invoices", patientId] });
      success("Factura cancelada", "La factura fue cancelada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo cancelar la factura. Inténtalo de nuevo.";
      error("Error al cancelar factura", message);
    },
  });
}

// ─── useSendInvoice ───────────────────────────────────────────────────────────

/**
 * POST /patients/{id}/invoices/{invoiceId}/send — sends an invoice.
 */
export function useSendInvoice(patientId: string, invoiceId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () =>
      apiPost<InvoiceResponse>(
        `/patients/${patientId}/invoices/${invoiceId}/send`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: invoiceQueryKey(patientId, invoiceId),
      });
      queryClient.invalidateQueries({ queryKey: ["invoices", patientId] });
      success("Factura enviada", "La factura fue enviada al paciente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo enviar la factura. Inténtalo de nuevo.";
      error("Error al enviar factura", message);
    },
  });
}
