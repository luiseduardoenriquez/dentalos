"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AddonsState {
  addons: Record<string, boolean>;
}

export interface AddonTogglePayload {
  addon: string;
  enabled: boolean;
}

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
  features: Record<string, boolean>;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const SETTINGS_QUERY_KEY = ["settings"] as const;
export const USAGE_QUERY_KEY = ["settings", "usage"] as const;
export const PLAN_LIMITS_QUERY_KEY = ["settings", "plan-limits"] as const;
export const ADDONS_QUERY_KEY = ["settings", "addons"] as const;
export const AVAILABLE_PLANS_QUERY_KEY = ["settings", "available-plans"] as const;

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

// ─── useAddons ───────────────────────────────────────────────────────────────

/**
 * Fetches the current add-on state for the tenant.
 *
 * @example
 * const { data } = useAddons();
 * const isVoiceEnabled = data?.addons.voice_dictation ?? false;
 */
export function useAddons() {
  return useQuery({
    queryKey: ADDONS_QUERY_KEY,
    queryFn: () => apiGet<AddonsState>("/settings/addons"),
    staleTime: 60_000, // 1 minute
  });
}

// ─── useToggleAddon ──────────────────────────────────────────────────────────

const ME_QUERY_KEY = ["auth", "me"] as const;

/**
 * PUT /settings/addons — toggles an add-on feature.
 * On success: invalidates addons cache + refetches /auth/me so
 * feature_flags update across the entire app.
 *
 * @example
 * const { mutate: toggleAddon, isPending } = useToggleAddon();
 * toggleAddon({ addon: "voice_dictation", enabled: true });
 */
export function useToggleAddon() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: AddonTogglePayload) =>
      apiPut<AddonsState>("/settings/addons", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADDONS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
      success("Complemento actualizado", "El cambio se aplicó correctamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo actualizar el complemento. Inténtalo de nuevo.";
      error("Error al actualizar complemento", message);
    },
  });
}

// ─── Plan Upgrade Types ──────────────────────────────────────────────────────

export interface AvailablePlanItem {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price_cents: number;
  currency: string;
  pricing_model: string;
  included_doctors: number;
  max_patients: number;
  max_doctors: number;
  max_users: number;
  max_storage_mb: number;
  features: Record<string, boolean>;
  sort_order: number;
}

export interface AvailablePlansResponse {
  current_plan_slug: string;
  plans: AvailablePlanItem[];
}

export interface ChangePlanResponse {
  success: boolean;
  new_plan_name: string;
  new_plan_slug: string;
  message: string;
}

// ─── useAvailablePlans ──────────────────────────────────────────────────────

/**
 * Fetches all available plans for the upgrade dialog.
 * Enabled only when the dialog is open to avoid unnecessary requests.
 */
export function useAvailablePlans(enabled = false) {
  return useQuery({
    queryKey: AVAILABLE_PLANS_QUERY_KEY,
    queryFn: () => apiGet<AvailablePlansResponse>("/settings/available-plans"),
    staleTime: 5 * 60 * 1000,
    enabled,
  });
}

// ─── useChangePlan ──────────────────────────────────────────────────────────

/**
 * POST /settings/change-plan — switches the tenant to a different plan.
 * On success: invalidates all settings queries and shows a toast.
 */
export function useChangePlan() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (planId: string) =>
      apiPost<ChangePlanResponse>("/settings/change-plan", { plan_id: planId }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: PLAN_LIMITS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: USAGE_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: AVAILABLE_PLANS_QUERY_KEY });
      success("Plan actualizado", data.message);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo cambiar el plan. Inténtalo de nuevo.";
      error("Error al cambiar plan", message);
    },
  });
}
