"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface EPSClaimProcedure {
  cups_code: string;
  description: string;
  quantity: number;
  unit_price_cents: number;
}

export interface EPSClaimResponse {
  id: string;
  patient_id: string;
  eps_code: string;
  eps_name: string;
  claim_type: "ambulatorio" | "urgencias" | "hospitalizacion" | "dental";
  status: "draft" | "submitted" | "acknowledged" | "paid" | "rejected" | "appealed";
  total_amount_cents: number;
  copay_amount_cents: number;
  procedures: EPSClaimProcedure[];
  reference_number: string | null;
  rejection_reason: string | null;
  submitted_at: string | null;
  acknowledged_at: string | null;
  response_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EPSClaimListResponse {
  items: EPSClaimResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface EPSClaimCreate {
  patient_id: string;
  eps_code: string;
  eps_name: string;
  claim_type: "ambulatorio" | "urgencias" | "hospitalizacion" | "dental";
  total_amount_cents: number;
  copay_amount_cents: number;
  procedures?: EPSClaimProcedure[];
}

export interface AgingReport {
  "0_30": number;
  "31_60": number;
  "61_90": number;
  "90_plus": number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const EPS_CLAIMS_QUERY_KEY = ["eps-claims"] as const;

export const epsClaimsQueryKey = (
  page: number,
  pageSize: number,
  status?: string,
) => ["eps-claims", page, pageSize, status ?? "all"] as const;

export const epsClaimQueryKey = (claimId: string) =>
  ["eps-claims", claimId] as const;

export const epsClaimsAgingQueryKey = () =>
  ["eps-claims", "aging"] as const;

// ─── useEPSClaims ─────────────────────────────────────────────────────────────

/**
 * Paginated list of EPS claims with optional status filter.
 */
export function useEPSClaims(
  page: number,
  pageSize: number,
  status?: string,
) {
  const queryParams: Record<string, unknown> = {
    page,
    page_size: pageSize,
    ...(status && status !== "all" && { status }),
  };

  return useQuery({
    queryKey: epsClaimsQueryKey(page, pageSize, status),
    queryFn: () =>
      apiGet<EPSClaimListResponse>(
        `/billing/eps-claims${buildQueryString(queryParams)}`,
      ),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useEPSClaim ──────────────────────────────────────────────────────────────

/**
 * Single EPS claim by ID.
 */
export function useEPSClaim(claimId: string) {
  return useQuery({
    queryKey: epsClaimQueryKey(claimId),
    queryFn: () =>
      apiGet<EPSClaimResponse>(`/billing/eps-claims/${claimId}`),
    enabled: Boolean(claimId),
    staleTime: 60_000,
  });
}

// ─── useCreateEPSClaim ────────────────────────────────────────────────────────

/**
 * POST /billing/eps-claims — creates a new EPS claim draft.
 */
export function useCreateEPSClaim() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: EPSClaimCreate) =>
      apiPost<EPSClaimResponse>("/billing/eps-claims", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EPS_CLAIMS_QUERY_KEY });
      success("Reclamación creada", "La reclamación EPS fue creada como borrador.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear la reclamación. Inténtalo de nuevo.";
      error("Error al crear reclamación", message);
    },
  });
}

// ─── useUpdateEPSClaim ────────────────────────────────────────────────────────

/**
 * PUT /billing/eps-claims/{id} — updates an existing EPS claim.
 */
export function useUpdateEPSClaim(claimId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Partial<EPSClaimCreate>) =>
      apiPut<EPSClaimResponse>(`/billing/eps-claims/${claimId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: epsClaimQueryKey(claimId) });
      queryClient.invalidateQueries({ queryKey: EPS_CLAIMS_QUERY_KEY });
      success("Reclamación actualizada", "Los datos de la reclamación fueron guardados.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar la reclamación. Inténtalo de nuevo.";
      error("Error al actualizar reclamación", message);
    },
  });
}

// ─── useSubmitEPSClaim ────────────────────────────────────────────────────────

/**
 * POST /billing/eps-claims/{id}/submit — submits a draft claim to the EPS.
 */
export function useSubmitEPSClaim(claimId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () =>
      apiPost<EPSClaimResponse>(`/billing/eps-claims/${claimId}/submit`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: epsClaimQueryKey(claimId) });
      queryClient.invalidateQueries({ queryKey: EPS_CLAIMS_QUERY_KEY });
      success("Reclamación enviada a la EPS", "La reclamación fue enviada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo enviar la reclamación. Inténtalo de nuevo.";
      error("Error al enviar reclamación", message);
    },
  });
}

// ─── useSyncEPSClaimStatus ────────────────────────────────────────────────────

/**
 * POST /billing/eps-claims/{id}/sync-status — syncs the claim status from the EPS.
 */
export function useSyncEPSClaimStatus(claimId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () =>
      apiPost<EPSClaimResponse>(`/billing/eps-claims/${claimId}/sync-status`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: epsClaimQueryKey(claimId) });
      queryClient.invalidateQueries({ queryKey: EPS_CLAIMS_QUERY_KEY });
      success("Estado sincronizado", "El estado de la reclamación fue actualizado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo sincronizar el estado. Inténtalo de nuevo.";
      error("Error al sincronizar estado", message);
    },
  });
}

// ─── useEPSClaimsAging ────────────────────────────────────────────────────────

/**
 * GET /billing/eps-claims/aging — returns aging buckets for outstanding claims.
 */
export function useEPSClaimsAging() {
  return useQuery({
    queryKey: epsClaimsAgingQueryKey(),
    queryFn: () => apiGet<AgingReport>("/billing/eps-claims/aging"),
    staleTime: 5 * 60_000,
  });
}
