"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface OdontogramSettings {
  /** Display mode for the odontogram: classic grid or anatomic arch view */
  default_view: "classic" | "anatomic";
  /** Default zoom level when opening the odontogram */
  default_zoom: "full" | "quadrant";
  /** Whether to auto-save the odontogram during voice dictation sessions */
  auto_save_dictation: boolean;
  /** Custom condition color overrides keyed by condition code */
  condition_colors: Record<string, string>;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const ODONTOGRAM_SETTINGS_KEY = ["settings", "odontogram"] as const;

// ─── useOdontogramSettings ────────────────────────────────────────────────────

/**
 * Fetches odontogram-specific settings for the current tenant.
 * Includes default_view (classic | anatomic), zoom, and voice auto-save.
 *
 * @example
 * const { data: settings } = useOdontogramSettings();
 * const viewMode = settings?.default_view ?? "classic";
 */
export function useOdontogramSettings() {
  return useQuery({
    queryKey: ODONTOGRAM_SETTINGS_KEY,
    queryFn: () => apiGet<OdontogramSettings>("/settings/odontogram"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// ─── useUpdateOdontogramSettings ──────────────────────────────────────────────

/**
 * PUT /settings/odontogram — updates odontogram settings.
 * On success: invalidates the settings cache.
 *
 * @example
 * const { mutate: update } = useUpdateOdontogramSettings();
 * update({ default_view: "anatomic" });
 */
export function useUpdateOdontogramSettings() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Partial<OdontogramSettings>) =>
      apiPut<OdontogramSettings>("/settings/odontogram", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ODONTOGRAM_SETTINGS_KEY });
      success(
        "Configuracion del odontograma actualizada",
        "Los cambios se aplicaran al abrir el proximo odontograma.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo guardar la configuracion. Intentalo de nuevo.";
      error("Error al guardar configuracion del odontograma", message);
    },
  });
}
