"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ReferralResponse {
  id: string;
  patient_id: string;
  from_doctor_id: string;
  from_doctor_name: string | null;
  to_doctor_id: string;
  to_doctor_name: string | null;
  reason: string;
  priority: "urgent" | "normal" | "low";
  specialty: string | null;
  status: "pending" | "accepted" | "completed" | "declined";
  notes: string | null;
  accepted_at: string | null;
  completed_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReferralListResponse {
  items: ReferralResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReferralCreate {
  to_doctor_id: string;
  reason: string;
  priority?: string;
  specialty?: string | null;
  notes?: string | null;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const REFERRALS_QUERY_KEY = ["referrals"] as const;
export const referralsQueryKey = (patientId: string, page: number, pageSize: number) =>
  ["referrals", patientId, page, pageSize] as const;

// ─── usePatientReferrals ─────────────────────────────────────────────────────

export function usePatientReferrals(
  patientId: string,
  page: number = 1,
  pageSize: number = 20,
) {
  return useQuery({
    queryKey: referralsQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<ReferralListResponse>(
        `/patients/${patientId}/referrals${buildQueryString({ page, page_size: pageSize })}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 60_000,
  });
}

// ─── Query Keys (incoming) ──────────────────────────────────────────────────

export const incomingReferralsQueryKey = (page: number, pageSize: number) =>
  ["referrals", "incoming", page, pageSize] as const;

// ─── useIncomingReferrals ───────────────────────────────────────────────────

export function useIncomingReferrals(page: number = 1, pageSize: number = 5) {
  return useQuery({
    queryKey: incomingReferralsQueryKey(page, pageSize),
    queryFn: () =>
      apiGet<ReferralListResponse>(
        `/referrals/incoming${buildQueryString({ page, page_size: pageSize })}`,
      ),
    staleTime: 60_000,
  });
}

// ─── useCreateReferral ───────────────────────────────────────────────────────

export function useCreateReferral(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: ReferralCreate) =>
      apiPost<ReferralResponse>(`/patients/${patientId}/referrals`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REFERRALS_QUERY_KEY });
      success("Referencia creada", "La referencia fue enviada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo crear la referencia.";
      error("Error al crear referencia", message);
    },
  });
}

// ─── useUpdateReferral ───────────────────────────────────────────────────────

export function useUpdateReferral() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      referralId,
      status,
      notes,
    }: {
      referralId: string;
      status: string;
      notes?: string | null;
    }) =>
      apiClient
        .put<ReferralResponse>(`/referrals/${referralId}`, { status, notes })
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REFERRALS_QUERY_KEY });
      success("Referencia actualizada", "El estado de la referencia fue actualizado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar la referencia.";
      error("Error al actualizar", message);
    },
  });
}
