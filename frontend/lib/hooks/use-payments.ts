"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PaymentResponse {
  id: string;
  invoice_id: string;
  patient_id: string;
  amount: number; // cents
  payment_method: "cash" | "card" | "transfer" | "other";
  reference_number: string | null;
  received_by: string;
  notes: string | null;
  payment_date: string;
  created_at: string;
  updated_at: string;
}

export interface PaymentListResponse {
  items: PaymentResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaymentCreate {
  amount: number; // cents, > 0
  payment_method: "cash" | "card" | "transfer" | "other";
  reference_number?: string | null;
  notes?: string | null;
}

export interface InstallmentResponse {
  id: string;
  plan_id: string;
  installment_number: number;
  amount: number; // cents
  due_date: string;
  status: "pending" | "paid" | "overdue";
  paid_at: string | null;
  payment_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentPlanResponse {
  id: string;
  invoice_id: string;
  patient_id: string;
  total_amount: number; // cents
  num_installments: number;
  status: "active" | "completed" | "cancelled";
  created_by: string;
  is_active: boolean;
  installments: InstallmentResponse[];
  created_at: string;
  updated_at: string;
}

export interface PaymentPlanCreate {
  num_installments: number; // 2-24
  first_due_date: string; // ISO date
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const paymentsQueryKey = (
  patientId: string,
  invoiceId: string,
  page: number,
  pageSize: number,
) => ["payments", patientId, invoiceId, page, pageSize] as const;

export const paymentPlanQueryKey = (
  patientId: string,
  invoiceId: string,
) => ["payment-plan", patientId, invoiceId] as const;

// ─── usePayments ──────────────────────────────────────────────────────────────

/**
 * Paginated list of payments for an invoice.
 */
export function usePayments(
  patientId: string,
  invoiceId: string,
  page = 1,
  pageSize = 20,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: paymentsQueryKey(patientId, invoiceId, page, pageSize),
    queryFn: () =>
      apiGet<PaymentListResponse>(
        `/patients/${patientId}/invoices/${invoiceId}/payments${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId) && Boolean(invoiceId),
    staleTime: 30_000,
  });
}

// ─── useRecordPayment ─────────────────────────────────────────────────────────

/**
 * POST /patients/{pid}/invoices/{iid}/payments — records a payment.
 */
export function useRecordPayment(patientId: string, invoiceId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: PaymentCreate) =>
      apiPost<PaymentResponse>(
        `/patients/${patientId}/invoices/${invoiceId}/payments`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["payments", patientId, invoiceId],
      });
      queryClient.invalidateQueries({
        queryKey: ["invoices", patientId],
      });
      success("Pago registrado", "El pago fue registrado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar el pago. Inténtalo de nuevo.";
      error("Error al registrar pago", message);
    },
  });
}

// ─── usePaymentPlan ───────────────────────────────────────────────────────────

/**
 * GET /patients/{pid}/invoices/{iid}/payment-plan — active payment plan.
 */
export function usePaymentPlan(patientId: string, invoiceId: string) {
  return useQuery({
    queryKey: paymentPlanQueryKey(patientId, invoiceId),
    queryFn: () =>
      apiGet<PaymentPlanResponse>(
        `/patients/${patientId}/invoices/${invoiceId}/payment-plan`,
      ),
    enabled: Boolean(patientId) && Boolean(invoiceId),
    staleTime: 60_000,
  });
}

// ─── useCreatePaymentPlan ─────────────────────────────────────────────────────

/**
 * POST /patients/{pid}/invoices/{iid}/payment-plan — creates a payment plan.
 */
export function useCreatePaymentPlan(patientId: string, invoiceId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: PaymentPlanCreate) =>
      apiPost<PaymentPlanResponse>(
        `/patients/${patientId}/invoices/${invoiceId}/payment-plan`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: paymentPlanQueryKey(patientId, invoiceId),
      });
      success(
        "Plan de pagos creado",
        "El plan de pagos fue creado exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el plan de pagos. Inténtalo de nuevo.";
      error("Error al crear plan de pagos", message);
    },
  });
}

// ─── usePayInstallment ────────────────────────────────────────────────────────

/**
 * POST /patients/{pid}/invoices/{iid}/payment-plan/{num}/pay — pay an installment.
 */
export function usePayInstallment(patientId: string, invoiceId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      installmentNumber,
      data,
    }: {
      installmentNumber: number;
      data: PaymentCreate;
    }) =>
      apiPost<PaymentResponse>(
        `/patients/${patientId}/invoices/${invoiceId}/payment-plan/${installmentNumber}/pay`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: paymentPlanQueryKey(patientId, invoiceId),
      });
      queryClient.invalidateQueries({
        queryKey: ["payments", patientId, invoiceId],
      });
      queryClient.invalidateQueries({
        queryKey: ["invoices", patientId],
      });
      success("Cuota pagada", "La cuota fue pagada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar el pago de la cuota. Inténtalo de nuevo.";
      error("Error al pagar cuota", message);
    },
  });
}
