"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Patient {
  id: string;
  document_type: string;
  document_number: string;
  first_name: string;
  last_name: string;
  full_name: string;
  birthdate: string | null;
  gender: string | null;
  blood_type: string | null;
  phone: string | null;
  phone_secondary: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  state_province: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  insurance_provider: string | null;
  insurance_policy_number: string | null;
  allergies: string[];
  chronic_conditions: string[];
  referral_source: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface PatientListItem {
  id: string;
  document_type: string;
  document_number: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PaginatedPatients {
  items: PatientListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PatientSearchResult {
  id: string;
  full_name: string;
  document_type: string;
  document_number: string;
  phone: string | null;
  is_active: boolean;
}

export interface PatientsQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean | "all";
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const PATIENTS_QUERY_KEY = ["patients"] as const;
export const patientQueryKey = (id: string) => ["patients", id] as const;
export const patientSearchQueryKey = (q: string) => ["patients", "search", q] as const;

// ─── usePatients ──────────────────────────────────────────────────────────────

/**
 * Paginated list of patients with filtering, sorting, and search.
 *
 * @example
 * const { data, isLoading } = usePatients({ page: 1, page_size: 20, search: "Ana" });
 */
export function usePatients(params: PatientsQueryParams = {}) {
  const { page = 1, page_size = 20, search, is_active, sort_by, sort_order } = params;

  // Build clean query params — omit undefined/null/"all"
  const queryParams: Record<string, unknown> = { page, page_size };
  if (search) queryParams.search = search;
  if (is_active !== undefined && is_active !== "all") queryParams.is_active = is_active;
  if (sort_by) queryParams.sort_by = sort_by;
  if (sort_order) queryParams.sort_order = sort_order;

  return useQuery({
    queryKey: [...PATIENTS_QUERY_KEY, queryParams],
    queryFn: () => apiGet<PaginatedPatients>(`/patients${buildQueryString(queryParams)}`),
    staleTime: 30_000, // 30 seconds
    placeholderData: (previousData) => previousData,
  });
}

// ─── usePatient ───────────────────────────────────────────────────────────────

/**
 * Single patient by ID.
 * Only fetches when id is a non-empty string.
 *
 * @example
 * const { data: patient, isLoading } = usePatient(id);
 */
export function usePatient(id: string | null | undefined) {
  return useQuery({
    queryKey: patientQueryKey(id ?? ""),
    queryFn: () => apiGet<Patient>(`/patients/${id}`),
    enabled: Boolean(id),
    staleTime: 60_000, // 1 minute
  });
}

// ─── useCreatePatient ─────────────────────────────────────────────────────────

/**
 * POST /patients — creates a new patient.
 * On success: invalidates the patients list and shows a success toast.
 *
 * @example
 * const { mutate: createPatient, isPending } = useCreatePatient();
 * createPatient(formData, { onSuccess: (patient) => router.push(`/patients/${patient.id}`) });
 */
export function useCreatePatient() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Record<string, unknown>) => apiPost<Patient>("/patients", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
      success("Paciente registrado", "El paciente fue creado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo registrar el paciente. Inténtalo de nuevo.";
      error("Error al registrar paciente", message);
    },
  });
}

// ─── useUpdatePatient ─────────────────────────────────────────────────────────

/**
 * PUT /patients/{id} — updates an existing patient.
 * On success: invalidates the individual patient cache and the list.
 *
 * @example
 * const { mutate: updatePatient, isPending } = useUpdatePatient();
 * updatePatient({ id: patientId, data: formData });
 */
export function useUpdatePatient() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      apiPut<Patient>(`/patients/${id}`, data),
    onSuccess: (patient) => {
      queryClient.invalidateQueries({ queryKey: patientQueryKey(patient.id) });
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
      success("Cambios guardados", "Los datos del paciente fueron actualizados.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar el paciente. Inténtalo de nuevo.";
      error("Error al actualizar paciente", message);
    },
  });
}

// ─── useDeactivatePatient ─────────────────────────────────────────────────────

/**
 * POST /patients/{id}/deactivate — soft-deletes a patient.
 * On success: invalidates queries and shows a toast.
 *
 * @example
 * const { mutate: deactivate } = useDeactivatePatient();
 * deactivate(patientId);
 */
export function useDeactivatePatient() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (id: string) => apiPost<{ message: string }>(`/patients/${id}/deactivate`),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: patientQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
      success("Paciente desactivado", "El paciente fue marcado como inactivo.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo desactivar el paciente. Inténtalo de nuevo.";
      error("Error al desactivar paciente", message);
    },
  });
}

// ─── useSearchPatients ────────────────────────────────────────────────────────

/**
 * Debounced patient search using GET /patients/search?q=...
 * Only fires when query has at least 2 characters.
 * Returns empty results immediately when query is too short (no loading flash).
 *
 * @param query - Raw search string (not yet debounced — hook handles the debounce)
 * @param debounceMs - Debounce delay in ms (default: 300)
 *
 * @example
 * const { data, isLoading } = useSearchPatients(inputValue);
 */
export function useSearchPatients(query: string, debounceMs = 300) {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, debounceMs);
    return () => clearTimeout(timer);
  }, [query, debounceMs]);

  const isQueryValid = debouncedQuery.length >= 2;

  return useQuery({
    queryKey: patientSearchQueryKey(debouncedQuery),
    queryFn: () =>
      apiGet<PatientSearchResult[]>(`/patients/search${buildQueryString({ q: debouncedQuery })}`),
    enabled: isQueryValid,
    staleTime: 30_000,
    placeholderData: [],
  });
}
