"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface OrthoCaseResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  treatment_plan_id: string | null;
  case_number: string;
  status: string;
  angle_class: string | null;
  malocclusion_type: string | null;
  appliance_type: string;
  estimated_duration_months: number | null;
  actual_start_date: string | null;
  actual_end_date: string | null;
  total_cost_estimated: number; // cents
  initial_payment: number; // cents
  monthly_payment: number; // cents
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrthoCaseListItem {
  id: string;
  case_number: string;
  status: string;
  appliance_type: string;
  doctor_id: string;
  total_cost_estimated: number; // cents
  visit_count: number;
  created_at: string;
}

export interface OrthoCaseListResponse {
  items: OrthoCaseListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrthoCaseCreate {
  appliance_type: string;
  angle_class?: string | null;
  malocclusion_type?: string | null;
  treatment_plan_id?: string | null;
  estimated_duration_months?: number | null;
  total_cost_estimated?: number;
  initial_payment?: number;
  monthly_payment?: number;
  notes?: string | null;
}

export interface OrthoCaseUpdate {
  appliance_type?: string;
  angle_class?: string | null;
  malocclusion_type?: string | null;
  treatment_plan_id?: string | null;
  estimated_duration_months?: number | null;
  total_cost_estimated?: number;
  initial_payment?: number;
  monthly_payment?: number;
  notes?: string | null;
}

export interface BondingToothInput {
  tooth_number: number;
  bracket_status: string;
  bracket_type?: string | null;
  slot_size?: string | null;
  wire_type?: string | null;
  band?: boolean;
  notes?: string | null;
}

export interface BondingRecordCreate {
  notes?: string | null;
  teeth: BondingToothInput[];
}

export interface BondingToothResponse {
  id: string;
  tooth_number: number;
  bracket_status: string;
  bracket_type: string | null;
  slot_size: string | null;
  wire_type: string | null;
  band: boolean;
  notes: string | null;
}

export interface BondingRecordResponse {
  id: string;
  ortho_case_id: string;
  recorded_by: string;
  notes: string | null;
  teeth: BondingToothResponse[];
  created_at: string;
  updated_at: string;
}

export interface BondingRecordListItem {
  id: string;
  recorded_by: string;
  tooth_count: number;
  created_at: string;
}

export interface BondingRecordListResponse {
  items: BondingRecordListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrthoVisitCreate {
  visit_date: string;
  wire_upper?: string | null;
  wire_lower?: string | null;
  elastics?: string | null;
  adjustments?: string | null;
  next_visit_date?: string | null;
  payment_amount?: number;
  notes?: string | null;
}

export interface OrthoVisitUpdate {
  wire_upper?: string | null;
  wire_lower?: string | null;
  elastics?: string | null;
  adjustments?: string | null;
  next_visit_date?: string | null;
  payment_status?: string | null;
  payment_amount?: number | null;
}

export interface OrthoVisitResponse {
  id: string;
  ortho_case_id: string;
  visit_number: number;
  doctor_id: string;
  visit_date: string;
  wire_upper: string | null;
  wire_lower: string | null;
  elastics: string | null;
  adjustments: string | null;
  next_visit_date: string | null;
  payment_status: string;
  payment_amount: number; // cents
  payment_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrthoVisitListResponse {
  items: OrthoVisitResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface MaterialCreate {
  inventory_item_id: string;
  visit_id?: string | null;
  quantity_used: number;
  notes?: string | null;
}

export interface MaterialResponse {
  id: string;
  ortho_case_id: string;
  visit_id: string | null;
  inventory_item_id: string;
  quantity_used: number;
  notes: string | null;
  created_by: string;
  created_at: string;
}

export interface MaterialListResponse {
  items: MaterialResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrthoCaseSummary {
  case_id: string;
  status: string;
  total_visits: number;
  visits_paid: number;
  visits_pending: number;
  total_collected: number; // cents
  total_expected: number; // cents
  balance_remaining: number; // cents
  materials_count: number;
  last_visit_date: string | null;
  next_visit_date: string | null;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const ORTHO_CASES_KEY = ["ortho_cases"] as const;

export const orthoCasesQueryKey = (
  patientId: string,
  page: number,
  pageSize: number,
) => ["ortho_cases", patientId, page, pageSize] as const;

export const orthoCaseQueryKey = (patientId: string, caseId: string) =>
  ["ortho_cases", patientId, caseId] as const;

export const orthoBondingQueryKey = (patientId: string, caseId: string) =>
  ["ortho_bonding", patientId, caseId] as const;

export const orthoVisitsQueryKey = (patientId: string, caseId: string) =>
  ["ortho_visits", patientId, caseId] as const;

export const orthoMaterialsQueryKey = (patientId: string, caseId: string) =>
  ["ortho_materials", patientId, caseId] as const;

export const orthoSummaryQueryKey = (patientId: string, caseId: string) =>
  ["ortho_summary", patientId, caseId] as const;

// ─── useOrthoCases ────────────────────────────────────────────────────────────

/**
 * Paginated list of orthodontic cases for a patient.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data, isLoading } = useOrthoCases(patientId, 1, 20);
 */
export function useOrthoCases(
  patientId: string,
  page: number,
  pageSize: number,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: orthoCasesQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<OrthoCaseListResponse>(
        `/patients/${patientId}/ortho-cases${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useOrthoCase ─────────────────────────────────────────────────────────────

/**
 * Single orthodontic case by ID.
 * Only fetches when both patientId and caseId are non-empty strings.
 *
 * @example
 * const { data: orthoCase, isLoading } = useOrthoCase(patientId, caseId);
 */
export function useOrthoCase(patientId: string, caseId: string) {
  return useQuery({
    queryKey: orthoCaseQueryKey(patientId, caseId),
    queryFn: () =>
      apiGet<OrthoCaseResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}`,
      ),
    enabled: Boolean(patientId) && Boolean(caseId),
    staleTime: 60_000,
  });
}

// ─── useCreateOrthoCase ───────────────────────────────────────────────────────

/**
 * POST /patients/{id}/ortho-cases — creates a new orthodontic case.
 * On success: invalidates the ortho cases list for that patient.
 *
 * @example
 * const { mutate: createCase, isPending } = useCreateOrthoCase(patientId);
 * createCase({ appliance_type: "brackets" }, { onSuccess: (c) => router.push(...) });
 */
export function useCreateOrthoCase(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: OrthoCaseCreate) =>
      apiPost<OrthoCaseResponse>(
        `/patients/${patientId}/ortho-cases`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["ortho_cases", patientId],
      });
      success("Caso creado", "El caso de ortodoncia fue creado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el caso de ortodoncia. Inténtalo de nuevo.";
      error("Error al crear caso", message);
    },
  });
}

// ─── useUpdateOrthoCase ───────────────────────────────────────────────────────

/**
 * PUT /patients/{id}/ortho-cases/{caseId} — updates an existing ortho case.
 * On success: invalidates the individual case cache and the list.
 *
 * @example
 * const { mutate: updateCase, isPending } = useUpdateOrthoCase(patientId);
 * updateCase({ caseId, data: { notes: "Revisión inicial completada" } });
 */
export function useUpdateOrthoCase(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      caseId,
      data,
    }: {
      caseId: string;
      data: OrthoCaseUpdate;
    }) =>
      apiPut<OrthoCaseResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}`,
        data,
      ),
    onSuccess: (orthoCase) => {
      queryClient.invalidateQueries({
        queryKey: orthoCaseQueryKey(patientId, orthoCase.id),
      });
      queryClient.invalidateQueries({
        queryKey: ["ortho_cases", patientId],
      });
      success(
        "Caso actualizado",
        "Los cambios fueron guardados exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar el caso. Inténtalo de nuevo.";
      error("Error al actualizar caso", message);
    },
  });
}

// ─── useTransitionOrthoCase ───────────────────────────────────────────────────

/**
 * POST /patients/{id}/ortho-cases/{caseId}/transition — changes the case status.
 * On success: invalidates the individual case and the list.
 *
 * @example
 * const { mutate: transition, isPending } = useTransitionOrthoCase(patientId);
 * transition({ caseId, targetStatus: "active_treatment" });
 */
export function useTransitionOrthoCase(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      caseId,
      targetStatus,
    }: {
      caseId: string;
      targetStatus: string;
    }) =>
      apiPost<OrthoCaseResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/transition`,
        { target_status: targetStatus },
      ),
    onSuccess: (orthoCase) => {
      queryClient.invalidateQueries({
        queryKey: orthoCaseQueryKey(patientId, orthoCase.id),
      });
      queryClient.invalidateQueries({
        queryKey: ["ortho_cases", patientId],
      });
      success(
        "Estado actualizado",
        "El estado del caso fue actualizado exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo cambiar el estado del caso. Inténtalo de nuevo.";
      error("Error al cambiar estado", message);
    },
  });
}

// ─── useOrthoBondingRecords ───────────────────────────────────────────────────

/**
 * Paginated list of bonding records for an ortho case.
 * Only fetches when patientId and caseId are non-empty strings.
 *
 * @example
 * const { data, isLoading } = useOrthoBondingRecords(patientId, caseId, 1, 20);
 */
export function useOrthoBondingRecords(
  patientId: string,
  caseId: string,
  page: number,
  pageSize: number,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: [...orthoBondingQueryKey(patientId, caseId), page, pageSize],
    queryFn: () =>
      apiGet<BondingRecordListResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/bonding${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId) && Boolean(caseId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useCreateBondingRecord ───────────────────────────────────────────────────

/**
 * POST /patients/{id}/ortho-cases/{caseId}/bonding — creates a bonding record.
 * On success: invalidates the bonding records list for that case.
 *
 * @example
 * const { mutate: createBonding, isPending } = useCreateBondingRecord(patientId, caseId);
 * createBonding({ teeth: [{ tooth_number: 11, bracket_status: "bonded" }] });
 */
export function useCreateBondingRecord(patientId: string, caseId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: BondingRecordCreate) =>
      apiPost<BondingRecordResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/bonding`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: orthoBondingQueryKey(patientId, caseId),
      });
      queryClient.invalidateQueries({
        queryKey: orthoCaseQueryKey(patientId, caseId),
      });
      success(
        "Cementado registrado",
        "El registro de cementado fue creado exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar el cementado. Inténtalo de nuevo.";
      error("Error al registrar cementado", message);
    },
  });
}

// ─── useOrthoVisits ───────────────────────────────────────────────────────────

/**
 * Paginated list of visits for an ortho case.
 * Only fetches when patientId and caseId are non-empty strings.
 *
 * @example
 * const { data, isLoading } = useOrthoVisits(patientId, caseId, 1, 20);
 */
export function useOrthoVisits(
  patientId: string,
  caseId: string,
  page: number,
  pageSize: number,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: [...orthoVisitsQueryKey(patientId, caseId), page, pageSize],
    queryFn: () =>
      apiGet<OrthoVisitListResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/visits${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId) && Boolean(caseId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useCreateOrthoVisit ──────────────────────────────────────────────────────

/**
 * POST /patients/{id}/ortho-cases/{caseId}/visits — adds a visit to an ortho case.
 * On success: invalidates the visits list and the case summary.
 *
 * @example
 * const { mutate: createVisit, isPending } = useCreateOrthoVisit(patientId, caseId);
 * createVisit({ visit_date: "2026-03-11", wire_upper: "0.014 NiTi" });
 */
export function useCreateOrthoVisit(patientId: string, caseId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: OrthoVisitCreate) =>
      apiPost<OrthoVisitResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/visits`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: orthoVisitsQueryKey(patientId, caseId),
      });
      queryClient.invalidateQueries({
        queryKey: orthoSummaryQueryKey(patientId, caseId),
      });
      success("Visita registrada", "La visita fue registrada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar la visita. Inténtalo de nuevo.";
      error("Error al registrar visita", message);
    },
  });
}

// ─── useUpdateOrthoVisit ──────────────────────────────────────────────────────

/**
 * PUT /patients/{id}/ortho-cases/{caseId}/visits/{visitId} — updates a visit.
 * On success: invalidates the visits list and the case summary.
 *
 * @example
 * const { mutate: updateVisit, isPending } = useUpdateOrthoVisit(patientId, caseId);
 * updateVisit({ visitId, data: { payment_status: "paid" } });
 */
export function useUpdateOrthoVisit(patientId: string, caseId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      visitId,
      data,
    }: {
      visitId: string;
      data: OrthoVisitUpdate;
    }) =>
      apiPut<OrthoVisitResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/visits/${visitId}`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: orthoVisitsQueryKey(patientId, caseId),
      });
      queryClient.invalidateQueries({
        queryKey: orthoSummaryQueryKey(patientId, caseId),
      });
      success("Visita actualizada", "Los cambios fueron guardados exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar la visita. Inténtalo de nuevo.";
      error("Error al actualizar visita", message);
    },
  });
}

// ─── useOrthoMaterials ────────────────────────────────────────────────────────

/**
 * Paginated list of materials used in an ortho case.
 * Only fetches when patientId and caseId are non-empty strings.
 *
 * @example
 * const { data, isLoading } = useOrthoMaterials(patientId, caseId, 1, 20);
 */
export function useOrthoMaterials(
  patientId: string,
  caseId: string,
  page: number,
  pageSize: number,
) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: [...orthoMaterialsQueryKey(patientId, caseId), page, pageSize],
    queryFn: () =>
      apiGet<MaterialListResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/materials${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId) && Boolean(caseId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useAddOrthoMaterial ──────────────────────────────────────────────────────

/**
 * POST /patients/{id}/ortho-cases/{caseId}/materials — records a material used.
 * On success: invalidates the materials list and the case summary.
 *
 * @example
 * const { mutate: addMaterial, isPending } = useAddOrthoMaterial(patientId, caseId);
 * addMaterial({ inventory_item_id: "uuid", quantity_used: 1 });
 */
export function useAddOrthoMaterial(patientId: string, caseId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: MaterialCreate) =>
      apiPost<MaterialResponse>(
        `/patients/${patientId}/ortho-cases/${caseId}/materials`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: orthoMaterialsQueryKey(patientId, caseId),
      });
      queryClient.invalidateQueries({
        queryKey: orthoSummaryQueryKey(patientId, caseId),
      });
      success(
        "Material registrado",
        "El material fue registrado exitosamente.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar el material. Inténtalo de nuevo.";
      error("Error al registrar material", message);
    },
  });
}

// ─── useOrthoCaseSummary ──────────────────────────────────────────────────────

/**
 * Summary statistics for an ortho case (visits, payments, materials).
 * Only fetches when both patientId and caseId are non-empty strings.
 *
 * @example
 * const { data: summary, isLoading } = useOrthoCaseSummary(patientId, caseId);
 */
export function useOrthoCaseSummary(patientId: string, caseId: string) {
  return useQuery({
    queryKey: orthoSummaryQueryKey(patientId, caseId),
    queryFn: () =>
      apiGet<OrthoCaseSummary>(
        `/patients/${patientId}/ortho-cases/${caseId}/summary`,
      ),
    enabled: Boolean(patientId) && Boolean(caseId),
    staleTime: 60_000,
  });
}
