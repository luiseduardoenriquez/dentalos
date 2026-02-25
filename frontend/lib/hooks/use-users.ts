"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TeamUser {
  id: string;
  email: string;
  name: string;
  role: string;
  phone: string | null;
  avatar_url: string | null;
  professional_license: string | null;
  specialties: string[] | null;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginatedUsers {
  items: TeamUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface UsersQueryParams {
  page?: number;
  page_size?: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const USERS_QUERY_KEY = ["users"] as const;
export const userQueryKey = (id: string) => ["users", id] as const;

// ─── useUsers ─────────────────────────────────────────────────────────────────

/**
 * Paginated list of users (team members) in the current tenant.
 *
 * @example
 * const { data, isLoading } = useUsers({ page: 1, page_size: 20 });
 */
export function useUsers(params: UsersQueryParams = {}) {
  const { page = 1, page_size = 20 } = params;
  const queryParams = { page, page_size };

  return useQuery({
    queryKey: [...USERS_QUERY_KEY, queryParams],
    queryFn: () => apiGet<PaginatedUsers>(`/users${buildQueryString(queryParams)}`),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useUser ──────────────────────────────────────────────────────────────────

/**
 * Single user by ID. Only fetches when id is truthy.
 *
 * @example
 * const { data: user, isLoading } = useUser(id);
 */
export function useUser(id: string | null | undefined) {
  return useQuery({
    queryKey: userQueryKey(id ?? ""),
    queryFn: () => apiGet<TeamUser>(`/users/${id}`),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

// ─── useUpdateUser ────────────────────────────────────────────────────────────

/**
 * PUT /users/{id} — updates a team member's profile.
 * On success: invalidates user + list queries.
 *
 * @example
 * const { mutate: updateUser } = useUpdateUser(id);
 * updateUser({ name: "María García", role: "assistant" });
 */
export function useUpdateUser(id: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Record<string, unknown>) => apiPut<TeamUser>(`/users/${id}`, data),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: userQueryKey(user.id) });
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      success("Usuario actualizado", "Los cambios del miembro del equipo fueron guardados.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar el usuario. Inténtalo de nuevo.";
      error("Error al actualizar usuario", message);
    },
  });
}

// ─── useDeactivateUser ────────────────────────────────────────────────────────

/**
 * POST /users/{id}/deactivate — deactivates a team member.
 * On success: invalidates queries and shows a toast.
 *
 * @example
 * const { mutate: deactivate } = useDeactivateUser(id);
 * deactivate();
 */
export function useDeactivateUser(id: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: () => apiPost<{ message: string }>(`/users/${id}/deactivate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      success("Usuario desactivado", "El miembro del equipo fue desactivado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo desactivar el usuario. Inténtalo de nuevo.";
      error("Error al desactivar usuario", message);
    },
  });
}
