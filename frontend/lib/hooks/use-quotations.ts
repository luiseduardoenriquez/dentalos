"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface QuotationItemResponse {
  id: string;
  service_id: string | null;
  description: string;
  quantity: number;
  unit_price: number; // cents
  discount: number; // cents
  subtotal: number; // cents
  sort_order: number;
}

export interface QuotationResponse {
  id: string;
  patient_id: string;
  quotation_number: string;
  treatment_plan_id: string | null;
  subtotal: number; // cents
  tax: number; // cents
  total: number; // cents
  valid_until: string;
  status: "draft" | "sent" | "approved" | "rejected" | "expired";
  days_until_expiry: number | null;
  items: QuotationItemResponse[];
  created_at: string;
}

export interface QuotationListResponse {
  items: QuotationResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface QuotationItemCreate {
  service_id?: string | null;
  description: string;
  quantity: number;
  unit_price: number; // cents
  discount?: number; // cents
}

export interface QuotationCreate {
  treatment_plan_id?: string | null;
  items?: QuotationItemCreate[];
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const QUOTATIONS_QUERY_KEY = ["quotations"] as const;

export const quotationsQueryKey = (
  patientId: string,
  page: number,
  pageSize: number,
) => ["quotations", patientId, page, pageSize] as const;

export const quotationQueryKey = (
  patientId: string,
  quotationId: string,
) => ["quotations", patientId, quotationId] as const;

// ─── useQuotations ────────────────────────────────────────────────────────────

/**
 * Paginated list of quotations for a patient.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data, isLoading } = useQuotations(patientId, 1, 20);
 */
export function useQuotations(
  patientId: string,
  page: number,
  pageSize: number,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: quotationsQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<QuotationListResponse>(
        `/patients/${patientId}/quotations${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useQuotation ─────────────────────────────────────────────────────────────

/**
 * Single quotation by ID.
 * Only fetches when both patientId and quotationId are non-empty strings.
 *
 * @example
 * const { data: quotation, isLoading } = useQuotation(patientId, quotationId);
 */
export function useQuotation(patientId: string, quotationId: string) {
  return useQuery({
    queryKey: quotationQueryKey(patientId, quotationId),
    queryFn: () =>
      apiGet<QuotationResponse>(
        `/patients/${patientId}/quotations/${quotationId}`,
      ),
    enabled: Boolean(patientId) && Boolean(quotationId),
    staleTime: 60_000,
  });
}

// ─── useCreateQuotation ───────────────────────────────────────────────────────

/**
 * POST /patients/{id}/quotations — creates a new quotation.
 * Can be generated from a treatment plan (treatment_plan_id) or with manual items.
 * On success: invalidates the quotations list for that patient.
 *
 * @example
 * const { mutate: createQuotation, isPending } = useCreateQuotation(patientId);
 * createQuotation({ treatment_plan_id: planId }, { onSuccess: (q) => router.push(`/quotations/${q.id}`) });
 */
export function useCreateQuotation(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: QuotationCreate) =>
      apiPost<QuotationResponse>(`/patients/${patientId}/quotations`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quotations", patientId] });
      success("Cotización creada", "La cotización fue generada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear la cotización. Inténtalo de nuevo.";
      error("Error al crear cotización", message);
    },
  });
}

// ─── useApproveQuotation ──────────────────────────────────────────────────────

/**
 * POST /patients/{id}/quotations/{quotationId}/approve — approves a quotation.
 * Requires the patient's digital signature (base64 PNG).
 * On success: invalidates quotation queries for the patient.
 *
 * @example
 * const { mutate: approveQuotation, isPending } = useApproveQuotation(patientId, quotationId);
 * approveQuotation({ signature_base64: "..." });
 */
export function useApproveQuotation(patientId: string, quotationId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: { signature_base64: string }) =>
      apiPost<QuotationResponse>(
        `/patients/${patientId}/quotations/${quotationId}/approve`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: quotationQueryKey(patientId, quotationId),
      });
      queryClient.invalidateQueries({ queryKey: ["quotations", patientId] });
      success("Cotización aprobada", "El paciente aprobó la cotización.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo aprobar la cotización. Inténtalo de nuevo.";
      error("Error al aprobar cotización", message);
    },
  });
}
