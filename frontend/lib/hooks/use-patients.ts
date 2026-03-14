"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";
import { cachePatients, getCachedPatients } from "@/lib/db/offline-data-service";
import { useOnlineStore } from "@/lib/stores/online-store";
import type { CachedPatient } from "@/lib/db/offline-db";

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
  portal_access: boolean;
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
  const isOnline = useOnlineStore((s) => s.is_online);

  // Build clean query params — omit undefined/null/"all"
  const queryParams: Record<string, unknown> = { page, page_size };
  if (search) queryParams.search = search;
  if (is_active !== undefined && is_active !== "all") queryParams.is_active = is_active;
  if (sort_by) queryParams.sort_by = sort_by;
  if (sort_order) queryParams.sort_order = sort_order;

  return useQuery({
    queryKey: [...PATIENTS_QUERY_KEY, queryParams],
    queryFn: async () => {
      // Offline: serve from IDB cache
      if (!isOnline) {
        const cached = await getCachedPatients();
        let items: PatientListItem[] = cached.map((p) => ({
          id: p.id,
          document_type: p.document_type,
          document_number: p.document_number,
          first_name: p.first_name,
          last_name: p.last_name,
          full_name: p.full_name,
          phone: p.phone,
          email: p.email,
          is_active: p.is_active,
          created_at: p.created_at,
        }));
        // Apply client-side filters
        if (search) {
          const q = search.toLowerCase();
          items = items.filter(
            (p) =>
              p.full_name.toLowerCase().includes(q) ||
              p.document_number.includes(q) ||
              (p.phone && p.phone.includes(q)),
          );
        }
        if (is_active !== undefined && is_active !== "all") {
          items = items.filter((p) => p.is_active === is_active);
        }
        const total = items.length;
        const start = (page - 1) * page_size;
        return { items: items.slice(start, start + page_size), total, page, page_size };
      }

      const result = await apiGet<PaginatedPatients>(`/patients${buildQueryString(queryParams)}`);
      // Write-through: cache to IDB for offline access
      try {
        const now = Date.now();
        const toCache: CachedPatient[] = result.items.map((p) => ({
          id: p.id,
          tenant_id: "",
          first_name: p.first_name,
          last_name: p.last_name,
          full_name: p.full_name,
          document_type: p.document_type,
          document_number: p.document_number,
          phone: p.phone,
          email: p.email,
          is_active: p.is_active,
          created_at: p.created_at,
          updated_at: "",
          synced_at: now,
        }));
        cachePatients(toCache).catch(() => {});
      } catch {
        // IDB write failure — non-blocking
      }
      return result;
    },
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
export function usePatient(id: string | null | undefined, includeDeleted = false) {
  const qs = includeDeleted ? "?include_deleted=true" : "";
  const is_online = useOnlineStore((s) => s.is_online);

  return useQuery({
    queryKey: [...patientQueryKey(id ?? ""), { includeDeleted }],
    queryFn: async () => {
      // Offline: try IDB cache
      if (!is_online) {
        const cached = await getCachedPatients().then((all) => all.find((p) => p.id === id));
        if (cached) return cached as unknown as Patient;
        throw new Error("Sin conexion y paciente no disponible offline");
      }
      return apiGet<Patient>(`/patients/${id}${qs}`);
    },
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

// ─── useReactivatePatient ─────────────────────────────────────────────────────

/**
 * POST /patients/{id}/reactivate — re-activates a deactivated patient.
 * On success: invalidates queries and shows a toast.
 *
 * @example
 * const { mutate: reactivate } = useReactivatePatient();
 * reactivate(patientId);
 */
export function useReactivatePatient() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (id: string) => apiPost<Patient>(`/patients/${id}/reactivate`),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: patientQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
      success("Paciente reactivado", "El paciente fue marcado como activo nuevamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo reactivar el paciente. Inténtalo de nuevo.";
      error("Error al reactivar paciente", message);
    },
  });
}

// ─── useManagePortalAccess ────────────────────────────────────────────────────

/**
 * POST /patients/{id}/portal-access — grant or revoke portal access.
 * On success: invalidates patient queries and shows a toast.
 *
 * @example
 * const { mutate: managePortal } = useManagePortalAccess();
 * managePortal({ id: patientId, action: "grant", invitation_channel: "email" });
 */
export function useManagePortalAccess() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      id,
      action,
      invitation_channel,
    }: {
      id: string;
      action: "grant" | "revoke";
      invitation_channel?: "email" | "whatsapp";
    }) =>
      apiPost<{ message: string }>(`/patients/${id}/portal-access`, {
        action,
        invitation_channel,
      }),
    onSuccess: (_data, { id, action }) => {
      queryClient.invalidateQueries({ queryKey: patientQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
      if (action === "grant") {
        success("Portal habilitado", "Se envió la invitación al paciente.");
      } else {
        success("Portal deshabilitado", "El acceso al portal fue revocado.");
      }
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo gestionar el acceso al portal.";
      error("Error", message);
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
    queryFn: async () => {
      const res = await apiGet<{ data: PatientSearchResult[]; count: number }>(
        `/patients/search${buildQueryString({ q: debouncedQuery })}`,
      );
      return res.data;
    },
    enabled: isQueryValid,
    staleTime: 30_000,
    placeholderData: [],
  });
}
