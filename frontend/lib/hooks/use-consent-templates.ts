"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SignaturePosition {
  role: string;
  label: string;
  required: boolean;
}

export interface ConsentTemplateResponse {
  id: string;
  name: string;
  category: string;
  description: string | null;
  content: string; // HTML
  signature_positions: SignaturePosition[] | null;
  version: number;
  is_builtin: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ConsentTemplateListResponse {
  items: ConsentTemplateResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConsentTemplateCreate {
  name: string;
  category: string;
  description?: string | null;
  content: string;
  signature_positions?: SignaturePosition[] | null;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const CONSENT_TEMPLATES_QUERY_KEY = ["consent-templates"] as const;
export const consentTemplateQueryKey = (templateId: string) =>
  ["consent-templates", templateId] as const;

// ─── useConsentTemplates ──────────────────────────────────────────────────────

/**
 * Fetches all available consent templates (including builtin).
 * Not scoped to a patient — returns all templates visible to this tenant.
 *
 * @example
 * const { data: templates, isLoading } = useConsentTemplates();
 */
export function useConsentTemplates() {
  return useQuery({
    queryKey: CONSENT_TEMPLATES_QUERY_KEY,
    queryFn: async () => {
      const response = await apiGet<ConsentTemplateListResponse>("/consent-templates");
      return response.items ?? [];
    },
    staleTime: 5 * 60_000, // 5 minutes — templates change rarely
  });
}

// ─── useConsentTemplate ───────────────────────────────────────────────────────

/**
 * Fetches a single consent template by ID.
 * Only fetches when templateId is a non-empty string.
 *
 * @example
 * const { data: template, isLoading } = useConsentTemplate(templateId);
 */
export function useConsentTemplate(templateId: string | null | undefined) {
  return useQuery({
    queryKey: consentTemplateQueryKey(templateId ?? ""),
    queryFn: () => apiGet<ConsentTemplateResponse>(`/consent-templates/${templateId}`),
    enabled: Boolean(templateId),
    staleTime: 5 * 60_000,
  });
}

// ─── useCreateConsentTemplate ─────────────────────────────────────────────────

/**
 * POST /consent-templates — creates a new custom consent template.
 * Requires clinic_owner role. On success: invalidates templates list.
 *
 * @example
 * const { mutate: createTemplate, isPending } = useCreateConsentTemplate();
 * createTemplate(formData, { onSuccess: (template) => router.push(`/settings/consents/${template.id}`) });
 */
export function useCreateConsentTemplate() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: ConsentTemplateCreate) =>
      apiPost<ConsentTemplateResponse>("/consent-templates", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CONSENT_TEMPLATES_QUERY_KEY });
      success("Plantilla creada", "La plantilla de consentimiento fue creada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear la plantilla. Inténtalo de nuevo.";
      error("Error al crear plantilla", message);
    },
  });
}

// ─── Types (Update) ──────────────────────────────────────────────────────────

export interface ConsentTemplateUpdate {
  name?: string | null;
  category?: string | null;
  description?: string | null;
  content?: string | null;
  signature_positions?: SignaturePosition[] | null;
}

// ─── useUpdateConsentTemplate ────────────────────────────────────────────────

/**
 * PUT /consent-templates/{id} — updates an existing consent template.
 * Requires consents:write permission. On success: invalidates templates list.
 */
export function useUpdateConsentTemplate() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: ConsentTemplateUpdate }) =>
      apiClient
        .put<ConsentTemplateResponse>(`/consent-templates/${templateId}`, data)
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CONSENT_TEMPLATES_QUERY_KEY });
      success("Plantilla actualizada", "La plantilla fue actualizada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar la plantilla.";
      error("Error al actualizar", message);
    },
  });
}

// ─── useDeleteConsentTemplate ────────────────────────────────────────────────

/**
 * DELETE /consent-templates/{id} — soft-deletes a consent template.
 * Requires clinic_owner role. On success: invalidates templates list.
 */
export function useDeleteConsentTemplate() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (templateId: string) =>
      apiClient
        .delete<ConsentTemplateResponse>(`/consent-templates/${templateId}`)
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CONSENT_TEMPLATES_QUERY_KEY });
      success("Plantilla eliminada", "La plantilla fue desactivada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo eliminar la plantilla.";
      error("Error al eliminar", message);
    },
  });
}
