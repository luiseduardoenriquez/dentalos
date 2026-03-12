"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface InjectionResponse {
  id: string;
  session_id: string;
  patient_id: string;
  zone_id: string;
  injection_type: string;
  product_name: string | null;
  dose_units: number | null;
  dose_volume_ml: number | null;
  depth: string | null;
  coordinates_x: number | null;
  coordinates_y: number | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  diagram_type: string;
  session_date: string;
  notes: string | null;
  injection_count: number;
  created_at: string;
  updated_at: string;
}

export interface SessionDetailResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  diagram_type: string;
  session_date: string;
  notes: string | null;
  injections: InjectionResponse[];
  created_at: string;
  updated_at: string;
}

export interface SessionListResponse {
  items: SessionResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface HistoryEntry {
  id: string;
  session_id: string;
  zone_id: string;
  action: string;
  injection_type: string;
  previous_data: Record<string, unknown> | null;
  new_data: Record<string, unknown> | null;
  performed_by: string | null;
  performed_by_name: string | null;
  created_at: string;
}

export interface HistoryListResponse {
  items: HistoryEntry[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface SnapshotResponse {
  id: string;
  patient_id: string;
  session_id: string | null;
  diagram_type: string;
  label: string | null;
  linked_record_id: string | null;
  created_by: string | null;
  created_at: string;
}

export interface SnapshotListResponse {
  items: SnapshotResponse[];
  total: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

const FA_KEY = "facial-aesthetics";

export const faSessionsKey = (patientId: string) => [FA_KEY, patientId] as const;
export const faSessionKey = (patientId: string, sessionId: string) =>
  [FA_KEY, patientId, sessionId] as const;
export const faHistoryKey = (patientId: string, sessionId: string) =>
  [FA_KEY, patientId, sessionId, "history"] as const;
export const faSnapshotsKey = (patientId: string) =>
  [FA_KEY, patientId, "snapshots"] as const;

// ─── Prefix helper ────────────────────────────────────────────────────────────

const prefix = (patientId: string) => `/patients/${patientId}/facial-aesthetics`;

// ─── useSessions ──────────────────────────────────────────────────────────────

export function useFASessions(
  patientId: string | null | undefined,
  params?: { page?: number; page_size?: number },
) {
  const queryParams: Record<string, unknown> = {};
  if (params?.page !== undefined) queryParams.page = params.page;
  if (params?.page_size !== undefined) queryParams.page_size = params.page_size;

  return useQuery({
    queryKey: [...faSessionsKey(patientId ?? ""), queryParams],
    queryFn: () =>
      apiGet<SessionListResponse>(
        `${prefix(patientId!)}${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 60_000,
  });
}

// ─── useSession ───────────────────────────────────────────────────────────────

export function useFASession(
  patientId: string | null | undefined,
  sessionId: string | null | undefined,
) {
  return useQuery({
    queryKey: faSessionKey(patientId ?? "", sessionId ?? ""),
    queryFn: () =>
      apiGet<SessionDetailResponse>(`${prefix(patientId!)}/${sessionId}`),
    enabled: Boolean(patientId) && Boolean(sessionId),
    staleTime: 30_000,
  });
}

// ─── useCreateSession ─────────────────────────────────────────────────────────

export function useCreateFASession() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      data,
    }: {
      patientId: string;
      data: { diagram_type?: string; session_date: string; notes?: string | null };
    }) => apiPost<SessionDetailResponse>(prefix(patientId), data),
    onSuccess: (_data, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: faSessionsKey(patientId) });
      success("Sesión creada", "La sesión de estética facial fue creada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo crear la sesión.";
      error("Error al crear sesión", message);
    },
  });
}

// ─── useUpdateSession ─────────────────────────────────────────────────────────

export function useUpdateFASession() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      sessionId,
      data,
    }: {
      patientId: string;
      sessionId: string;
      data: { diagram_type?: string; notes?: string | null };
    }) => apiPut<SessionDetailResponse>(`${prefix(patientId)}/${sessionId}`, data),
    onSuccess: (_data, { patientId, sessionId }) => {
      queryClient.invalidateQueries({ queryKey: faSessionsKey(patientId) });
      queryClient.invalidateQueries({ queryKey: faSessionKey(patientId, sessionId) });
      success("Sesión actualizada", "La sesión fue actualizada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar la sesión.";
      error("Error al actualizar sesión", message);
    },
  });
}

// ─── useDeleteSession ─────────────────────────────────────────────────────────

export function useDeleteFASession() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      sessionId,
    }: {
      patientId: string;
      sessionId: string;
    }) => apiDelete<{ message: string }>(`${prefix(patientId)}/${sessionId}`),
    onSuccess: (_data, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: faSessionsKey(patientId) });
      success("Sesión eliminada", "La sesión fue eliminada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo eliminar la sesión.";
      error("Error al eliminar sesión", message);
    },
  });
}

// ─── useAddInjection ──────────────────────────────────────────────────────────

export function useAddInjection() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      sessionId,
      data,
    }: {
      patientId: string;
      sessionId: string;
      data: Record<string, unknown>;
    }) =>
      apiPost<InjectionResponse>(
        `${prefix(patientId)}/${sessionId}/injections`,
        data,
      ),
    onSuccess: (_data, { patientId, sessionId }) => {
      queryClient.invalidateQueries({ queryKey: faSessionKey(patientId, sessionId) });
      queryClient.invalidateQueries({ queryKey: faSessionsKey(patientId) });
      success("Inyección registrada", "El punto de inyección fue registrado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo registrar la inyección.";
      error("Error al registrar inyección", message);
    },
  });
}

// ─── useUpdateInjection ───────────────────────────────────────────────────────

export function useUpdateInjection() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      sessionId,
      injectionId,
      data,
    }: {
      patientId: string;
      sessionId: string;
      injectionId: string;
      data: Record<string, unknown>;
    }) =>
      apiPut<InjectionResponse>(
        `${prefix(patientId)}/${sessionId}/injections/${injectionId}`,
        data,
      ),
    onSuccess: (_data, { patientId, sessionId }) => {
      queryClient.invalidateQueries({ queryKey: faSessionKey(patientId, sessionId) });
      success("Inyección actualizada", "Los datos de la inyección fueron actualizados.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar la inyección.";
      error("Error al actualizar inyección", message);
    },
  });
}

// ─── useRemoveInjection ───────────────────────────────────────────────────────

export function useRemoveInjection() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      sessionId,
      injectionId,
    }: {
      patientId: string;
      sessionId: string;
      injectionId: string;
    }) =>
      apiDelete<{ message: string }>(
        `${prefix(patientId)}/${sessionId}/injections/${injectionId}`,
      ),
    onSuccess: (_data, { patientId, sessionId }) => {
      queryClient.invalidateQueries({ queryKey: faSessionKey(patientId, sessionId) });
      queryClient.invalidateQueries({ queryKey: faSessionsKey(patientId) });
      success("Inyección eliminada", "El punto de inyección fue removido.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo eliminar la inyección.";
      error("Error al eliminar inyección", message);
    },
  });
}

// ─── useHistory ───────────────────────────────────────────────────────────────

export function useFAHistory(
  patientId: string,
  sessionId: string,
  params?: { cursor?: string; limit?: number },
) {
  const queryParams: Record<string, unknown> = {};
  if (params?.cursor) queryParams.cursor = params.cursor;
  if (params?.limit !== undefined) queryParams.limit = params.limit;

  return useQuery({
    queryKey: [...faHistoryKey(patientId, sessionId), queryParams],
    queryFn: () =>
      apiGet<HistoryListResponse>(
        `${prefix(patientId)}/${sessionId}/history${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId) && Boolean(sessionId),
    staleTime: 30_000,
  });
}

// ─── useCreateSnapshot ────────────────────────────────────────────────────────

export function useCreateFASnapshot() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({
      patientId,
      sessionId,
      data,
    }: {
      patientId: string;
      sessionId: string;
      data: { label?: string | null; linked_record_id?: string | null };
    }) =>
      apiPost<SnapshotResponse>(
        `${prefix(patientId)}/${sessionId}/snapshots`,
        data,
      ),
    onSuccess: (_data, { patientId }) => {
      queryClient.invalidateQueries({ queryKey: faSnapshotsKey(patientId) });
      success("Instantánea guardada", "La instantánea fue creada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo crear la instantánea.";
      error("Error al crear instantánea", message);
    },
  });
}

// ─── useSnapshots ─────────────────────────────────────────────────────────────

export function useFASnapshots(patientId: string | null | undefined) {
  return useQuery({
    queryKey: faSnapshotsKey(patientId ?? ""),
    queryFn: () =>
      apiGet<SnapshotListResponse>(`${prefix(patientId!)}/snapshots`),
    enabled: Boolean(patientId),
    staleTime: 60_000,
  });
}
