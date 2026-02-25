"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TreatmentPlanItemResponse {
  id: string;
  cups_code: string;
  cups_description: string;
  tooth_number: number | null;
  estimated_cost: number; // cents
  actual_cost: number | null; // cents
  priority_order: number;
  status: "pending" | "scheduled" | "completed" | "cancelled";
  procedure_id: string | null;
  created_at: string;
}

export interface TreatmentPlanResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "completed" | "cancelled";
  total_cost_estimated: number; // cents
  total_cost_actual: number; // cents
  progress_percent: number;
  signature_id: string | null;
  items: TreatmentPlanItemResponse[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TreatmentPlanListResponse {
  items: TreatmentPlanResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface TreatmentPlanItemCreate {
  cups_code: string;
  cups_description: string;
  tooth_number?: number | null;
  estimated_cost: number; // cents
}

export interface TreatmentPlanCreate {
  name: string;
  description?: string | null;
  auto_from_odontogram?: boolean;
  items?: TreatmentPlanItemCreate[];
}

export interface TreatmentPlanUpdate {
  name?: string;
  description?: string | null;
  status?: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const TREATMENT_PLANS_QUERY_KEY = ["treatment_plans"] as const;

export const treatmentPlansQueryKey = (
  patientId: string,
  page: number,
  pageSize: number,
) => ["treatment_plans", patientId, page, pageSize] as const;

export const treatmentPlanQueryKey = (patientId: string, planId: string) =>
  ["treatment_plans", patientId, planId] as const;

// ─── useTreatmentPlans ────────────────────────────────────────────────────────

/**
 * Paginated list of treatment plans for a patient.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data, isLoading } = useTreatmentPlans(patientId, 1, 20);
 */
export function useTreatmentPlans(
  patientId: string,
  page: number,
  pageSize: number,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: treatmentPlansQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<TreatmentPlanListResponse>(
        `/patients/${patientId}/treatment-plans${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useTreatmentPlan ─────────────────────────────────────────────────────────

/**
 * Single treatment plan by ID.
 * Only fetches when both patientId and planId are non-empty strings.
 *
 * @example
 * const { data: plan, isLoading } = useTreatmentPlan(patientId, planId);
 */
export function useTreatmentPlan(patientId: string, planId: string) {
  return useQuery({
    queryKey: treatmentPlanQueryKey(patientId, planId),
    queryFn: () =>
      apiGet<TreatmentPlanResponse>(
        `/patients/${patientId}/treatment-plans/${planId}`,
      ),
    enabled: Boolean(patientId) && Boolean(planId),
    staleTime: 60_000,
  });
}

// ─── useCreateTreatmentPlan ───────────────────────────────────────────────────

/**
 * POST /patients/{id}/treatment-plans — creates a new treatment plan.
 * On success: invalidates the treatment plans list for that patient.
 *
 * @example
 * const { mutate: createPlan, isPending } = useCreateTreatmentPlan(patientId);
 * createPlan({ name: "Plan 1", auto_from_odontogram: true }, { onSuccess: (plan) => router.push(...) });
 */
export function useCreateTreatmentPlan(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: TreatmentPlanCreate) =>
      apiPost<TreatmentPlanResponse>(
        `/patients/${patientId}/treatment-plans`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["treatment_plans", patientId],
      });
      success(
        "Plan creado",
        "El plan de tratamiento fue creado exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el plan de tratamiento. Inténtalo de nuevo.";
      error("Error al crear plan", message);
    },
  });
}

// ─── useUpdateTreatmentPlan ───────────────────────────────────────────────────

/**
 * PUT /patients/{id}/treatment-plans/{planId} — updates an existing plan.
 * On success: invalidates the individual plan cache and the list.
 *
 * @example
 * const { mutate: updatePlan, isPending } = useUpdateTreatmentPlan(patientId);
 * updatePlan({ planId, data: { name: "Nuevo nombre" } });
 */
export function useUpdateTreatmentPlan(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      planId,
      data,
    }: {
      planId: string;
      data: TreatmentPlanUpdate;
    }) =>
      apiPut<TreatmentPlanResponse>(
        `/patients/${patientId}/treatment-plans/${planId}`,
        data,
      ),
    onSuccess: (plan) => {
      queryClient.invalidateQueries({
        queryKey: treatmentPlanQueryKey(patientId, plan.id),
      });
      queryClient.invalidateQueries({
        queryKey: ["treatment_plans", patientId],
      });
      success("Plan actualizado", "Los cambios fueron guardados exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar el plan. Inténtalo de nuevo.";
      error("Error al actualizar plan", message);
    },
  });
}

// ─── useAddTreatmentPlanItem ──────────────────────────────────────────────────

/**
 * POST /patients/{id}/treatment-plans/{planId}/items — adds an item to a plan.
 * On success: invalidates the plan detail cache.
 *
 * @example
 * const { mutate: addItem, isPending } = useAddTreatmentPlanItem(patientId, planId);
 * addItem({ cups_code: "809101", cups_description: "Extracción", estimated_cost: 5000000 });
 */
export function useAddTreatmentPlanItem(patientId: string, planId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: TreatmentPlanItemCreate) =>
      apiPost<TreatmentPlanItemResponse>(
        `/patients/${patientId}/treatment-plans/${planId}/items`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: treatmentPlanQueryKey(patientId, planId),
      });
      success("Ítem agregado", "El procedimiento fue agregado al plan.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo agregar el procedimiento. Inténtalo de nuevo.";
      error("Error al agregar ítem", message);
    },
  });
}

// ─── useApproveTreatmentPlan ──────────────────────────────────────────────────

/**
 * POST /patients/{id}/treatment-plans/{planId}/approve — approves and activates a plan.
 * Requires a digital signature (base64 PNG).
 * On success: invalidates all treatment plan queries for the patient.
 *
 * @example
 * const { mutate: approvePlan, isPending } = useApproveTreatmentPlan(patientId, planId);
 * approvePlan({ signature_base64: "..." });
 */
export function useApproveTreatmentPlan(patientId: string, planId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: { signature_base64: string }) =>
      apiPost<TreatmentPlanResponse>(
        `/patients/${patientId}/treatment-plans/${planId}/approve`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["treatment_plans", patientId],
      });
      success(
        "Plan aprobado",
        "El plan de tratamiento fue aprobado y activado.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo aprobar el plan. Inténtalo de nuevo.";
      error("Error al aprobar plan", message);
    },
  });
}

// ─── useCancelTreatmentPlan ───────────────────────────────────────────────────

/**
 * POST /patients/{id}/treatment-plans/{planId}/cancel — cancels a treatment plan.
 * On success: invalidates all treatment plan queries for the patient.
 *
 * @example
 * const { mutate: cancelPlan, isPending } = useCancelTreatmentPlan(patientId, planId);
 * cancelPlan();
 */
export function useCancelTreatmentPlan(patientId: string, planId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () =>
      apiPost<TreatmentPlanResponse>(
        `/patients/${patientId}/treatment-plans/${planId}/cancel`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["treatment_plans", patientId],
      });
      success("Plan cancelado", "El plan de tratamiento fue cancelado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo cancelar el plan. Inténtalo de nuevo.";
      error("Error al cancelar plan", message);
    },
  });
}
