"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DentalLabResponse {
  id: string;
  name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DentalLabCreate {
  name: string;
  contact_name?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  city?: string | null;
  notes?: string | null;
}

export interface LabOrderResponse {
  id: string;
  patient_id: string;
  treatment_plan_id: string | null;
  lab_id: string | null;
  order_type: string;
  specifications: string | null;
  status: string;
  due_date: string | null;
  sent_at: string | null;
  ready_at: string | null;
  delivered_at: string | null;
  cost_cents: number | null;
  notes: string | null;
  created_by: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LabOrderCreate {
  patient_id: string;
  order_type: string;
  treatment_plan_id?: string | null;
  lab_id?: string | null;
  specifications?: string | null;
  due_date?: string | null;
  cost_cents?: number | null;
  notes?: string | null;
}

export interface LabOrderListResponse {
  items: LabOrderResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface LabOrderStatusUpdate {
  status: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const DENTAL_LABS_QUERY_KEY = ["dental-labs"] as const;

export const labOrdersQueryKey = (
  page: number,
  pageSize: number,
  status?: string,
  labId?: string,
) => ["lab-orders", page, pageSize, status, labId] as const;

export const labOrderQueryKey = (orderId: string) =>
  ["lab-orders", orderId] as const;

export const OVERDUE_LAB_ORDERS_QUERY_KEY = ["lab-orders", "overdue"] as const;

// ─── useDentalLabs ────────────────────────────────────────────────────────────

/**
 * Fetches all active dental labs.
 */
export function useDentalLabs() {
  return useQuery({
    queryKey: DENTAL_LABS_QUERY_KEY,
    queryFn: () => apiGet<DentalLabResponse[]>("/lab-orders/labs"),
    staleTime: 5 * 60_000,
  });
}

// ─── useCreateDentalLab ───────────────────────────────────────────────────────

/**
 * POST /lab-orders/labs — creates a new dental lab.
 */
export function useCreateDentalLab() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: DentalLabCreate) =>
      apiPost<DentalLabResponse>("/lab-orders/labs", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DENTAL_LABS_QUERY_KEY });
      success("Laboratorio creado", "El laboratorio fue registrado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el laboratorio. Inténtalo de nuevo.";
      error("Error al crear laboratorio", message);
    },
  });
}

// ─── useLabOrders ─────────────────────────────────────────────────────────────

/**
 * Paginated list of lab orders with optional filters.
 */
export function useLabOrders(
  page: number,
  pageSize: number,
  status?: string,
  labId?: string,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };
  if (status) queryParams.status = status;
  if (labId) queryParams.lab_id = labId;

  return useQuery({
    queryKey: labOrdersQueryKey(page, pageSize, status, labId),
    queryFn: () =>
      apiGet<LabOrderListResponse>(`/lab-orders${buildQueryString(queryParams)}`),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useLabOrder ──────────────────────────────────────────────────────────────

/**
 * Single lab order by ID.
 */
export function useLabOrder(orderId: string) {
  return useQuery({
    queryKey: labOrderQueryKey(orderId),
    queryFn: () => apiGet<LabOrderResponse>(`/lab-orders/${orderId}`),
    enabled: Boolean(orderId),
    staleTime: 60_000,
  });
}

// ─── useCreateLabOrder ────────────────────────────────────────────────────────

/**
 * POST /lab-orders — creates a new lab order.
 */
export function useCreateLabOrder() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: LabOrderCreate) =>
      apiPost<LabOrderResponse>("/lab-orders", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
      success(
        "Orden de laboratorio creada",
        "La orden fue registrada exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear la orden. Inténtalo de nuevo.";
      error("Error al crear orden", message);
    },
  });
}

// ─── useUpdateLabOrder ────────────────────────────────────────────────────────

/**
 * PUT /lab-orders/{orderId} — updates a lab order.
 */
export function useUpdateLabOrder(orderId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Partial<LabOrderCreate>) =>
      apiPut<LabOrderResponse>(`/lab-orders/${orderId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: labOrderQueryKey(orderId) });
      queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
      success("Orden actualizada", "Los cambios se guardaron correctamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar la orden. Inténtalo de nuevo.";
      error("Error al actualizar orden", message);
    },
  });
}

// ─── useAdvanceLabOrder ───────────────────────────────────────────────────────

/**
 * POST /lab-orders/{orderId}/advance — advances the order to its next status.
 */
export function useAdvanceLabOrder(orderId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () =>
      apiPost<LabOrderResponse>(`/lab-orders/${orderId}/advance`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: labOrderQueryKey(orderId) });
      queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
      success("Estado actualizado", "El estado de la orden fue avanzado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo avanzar el estado. Inténtalo de nuevo.";
      error("Error al avanzar estado", message);
    },
  });
}

// ─── useOverdueLabOrders ──────────────────────────────────────────────────────

/**
 * Fetches all overdue lab orders (past due date, not yet delivered).
 */
export function useOverdueLabOrders() {
  return useQuery({
    queryKey: OVERDUE_LAB_ORDERS_QUERY_KEY,
    queryFn: () => apiGet<LabOrderResponse[]>("/lab-orders/overdue"),
    staleTime: 60_000,
  });
}
