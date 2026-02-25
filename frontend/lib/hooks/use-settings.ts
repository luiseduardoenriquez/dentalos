"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ClinicSettings {
  name: string;
  phone: string | null;
  address: string | null;
  timezone: string;
  currency_code: string;
  locale: string;
  logo_url: string | null;
}

export interface UsageStats {
  patients_count: number;
  doctors_count: number;
  users_count: number;
  storage_used_mb: number;
}

export interface PlanLimitsSettings {
  plan_name: string;
  plan_price_monthly_cents: number;
  max_patients: number;
  max_doctors: number;
  max_users: number;
  max_storage_mb: number;
  features: string[];
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const SETTINGS_QUERY_KEY = ["settings"] as const;
export const USAGE_QUERY_KEY = ["settings", "usage"] as const;
export const PLAN_LIMITS_QUERY_KEY = ["settings", "plan-limits"] as const;

// ─── useSettings ──────────────────────────────────────────────────────────────

/**
 * Fetches the current tenant's clinic settings.
 * Stale time is 5 minutes — matches Redis TTL for tenant_meta.
 *
 * @example
 * const { data: settings, isLoading } = useSettings();
 */
export function useSettings() {
  return useQuery({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: () => apiGet<ClinicSettings>("/settings"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// ─── useUpdateSettings ────────────────────────────────────────────────────────

/**
 * PUT /settings — updates clinic settings.
 * On success: invalidates settings cache and shows a toast.
 *
 * @example
 * const { mutate: updateSettings, isPending } = useUpdateSettings();
 * updateSettings({ name: "Clínica Nueva Sonrisa", timezone: "America/Bogota" });
 */
export function useUpdateSettings() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Partial<ClinicSettings>) => apiPut<ClinicSettings>("/settings", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEY });
      success("Configuración guardada", "Los cambios de la clínica fueron actualizados.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo guardar la configuración. Inténtalo de nuevo.";
      error("Error al guardar configuración", message);
    },
  });
}

// ─── useUsage ─────────────────────────────────────────────────────────────────

/**
 * Fetches current usage statistics for the tenant (patients, doctors, storage).
 *
 * @example
 * const { data: usage, isLoading } = useUsage();
 */
export function useUsage() {
  return useQuery({
    queryKey: USAGE_QUERY_KEY,
    queryFn: () => apiGet<UsageStats>("/settings/usage"),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// ─── usePlanLimits ────────────────────────────────────────────────────────────

/**
 * Fetches the current plan limits and feature list for the tenant.
 * Stale time is 10 minutes — matches Redis TTL for plan_limits.
 *
 * @example
 * const { data: limits, isLoading } = usePlanLimits();
 */
export function usePlanLimits() {
  return useQuery({
    queryKey: PLAN_LIMITS_QUERY_KEY,
    queryFn: () => apiGet<PlanLimitsSettings>("/settings/plan-limits"),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
