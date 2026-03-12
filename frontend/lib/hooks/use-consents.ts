"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ConsentStatus = "draft" | "pending_signatures" | "signed" | "voided";

export interface ConsentResponse {
  id: string;
  patient_id: string;
  doctor_id: string;
  template_id: string | null;
  title: string;
  status: ConsentStatus;
  content_rendered: string; // HTML with patient data injected
  content_hash: string | null;
  signed_at: string | null;
  locked_at: string | null;
  voided_at: string | null;
  voided_by: string | null;
  void_reason: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConsentListResponse {
  items: ConsentResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConsentCreate {
  template_id: string;
}

export interface ConsentSignPayload {
  signature_base64: string;
  signer_type: "patient" | "doctor";
}

export interface ConsentVoidPayload {
  reason: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const consentsQueryKey = (patientId: string, page: number, pageSize: number) =>
  ["consents", patientId, page, pageSize] as const;

export const consentQueryKey = (patientId: string, consentId: string) =>
  ["consents", patientId, consentId] as const;

// ─── useConsents ──────────────────────────────────────────────────────────────

/**
 * Paginated list of consents for a patient.
 * Only fetches when patientId is a non-empty string.
 *
 * @example
 * const { data, isLoading } = useConsents(patientId, 1, 20);
 */
export function useConsents(patientId: string, page: number, pageSize: number) {
  const queryParams: Record<string, unknown> = { page, page_size: pageSize };

  return useQuery({
    queryKey: consentsQueryKey(patientId, page, pageSize),
    queryFn: () =>
      apiGet<ConsentListResponse>(
        `/patients/${patientId}/consents${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(patientId),
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

// ─── useConsent ───────────────────────────────────────────────────────────────

/**
 * Fetches a single consent by ID for a patient.
 * Only fetches when both IDs are non-empty strings.
 *
 * @example
 * const { data: consent, isLoading } = useConsent(patientId, consentId);
 */
export function useConsent(patientId: string | null | undefined, consentId: string | null | undefined) {
  return useQuery({
    queryKey: consentQueryKey(patientId ?? "", consentId ?? ""),
    queryFn: () =>
      apiGet<ConsentResponse>(`/patients/${patientId}/consents/${consentId}`),
    enabled: Boolean(patientId) && Boolean(consentId),
    staleTime: 30_000,
  });
}

// ─── useCreateConsent ─────────────────────────────────────────────────────────

/**
 * POST /patients/{id}/consents — creates a new consent from a template.
 * On success: invalidates the consents list for that patient.
 *
 * @example
 * const { mutate: createConsent, isPending } = useCreateConsent(patientId);
 * createConsent({ template_id }, { onSuccess: (consent) => router.push(`.../consents/${consent.id}`) });
 */
export function useCreateConsent(patientId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: ConsentCreate) =>
      apiPost<ConsentResponse>(`/patients/${patientId}/consents`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consents", patientId] });
      success("Consentimiento creado", "El consentimiento fue creado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo crear el consentimiento. Inténtalo de nuevo.";
      error("Error al crear consentimiento", message);
    },
  });
}

// ─── useSignConsent ───────────────────────────────────────────────────────────

/**
 * POST /patients/{id}/consents/{consentId}/sign — submits a signature for a consent.
 * On success: invalidates the consent detail and the list.
 *
 * @example
 * const { mutate: signConsent, isPending } = useSignConsent(patientId, consentId);
 * signConsent({ signature_base64, signer_type: "patient" }, { onSuccess: () => router.back() });
 */
export function useSignConsent(patientId: string, consentId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: ConsentSignPayload) =>
      apiPost<ConsentResponse>(
        `/patients/${patientId}/consents/${consentId}/sign`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: consentQueryKey(patientId, consentId) });
      queryClient.invalidateQueries({ queryKey: ["consents", patientId] });
      success("Consentimiento firmado", "La firma fue registrada exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo registrar la firma. Inténtalo de nuevo.";
      error("Error al firmar consentimiento", message);
    },
  });
}

// ─── useVoidConsent ───────────────────────────────────────────────────────────

/**
 * POST /patients/{id}/consents/{consentId}/void — voids a consent with a reason.
 * This action is irreversible. On success: invalidates related queries.
 *
 * @example
 * const { mutate: voidConsent, isPending } = useVoidConsent(patientId, consentId);
 * voidConsent({ reason }, { onSuccess: () => setDialogOpen(false) });
 */
export function useVoidConsent(patientId: string, consentId: string) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: ConsentVoidPayload) =>
      apiPost<ConsentResponse>(
        `/patients/${patientId}/consents/${consentId}/void`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: consentQueryKey(patientId, consentId) });
      queryClient.invalidateQueries({ queryKey: ["consents", patientId] });
      success("Consentimiento anulado", "El consentimiento fue anulado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo anular el consentimiento. Inténtalo de nuevo.";
      error("Error al anular consentimiento", message);
    },
  });
}

// ─── useConsentPdf ────────────────────────────────────────────────────────────

/**
 * Fetches the PDF blob for a signed consent and returns an object URL.
 * Only fetches when both IDs are non-empty strings.
 * The returned URL must be revoked when no longer needed to avoid memory leaks.
 *
 * @example
 * const { data: pdfUrl, isLoading } = useConsentPdf(patientId, consentId);
 * // Use pdfUrl in an <a href={pdfUrl} download> or <iframe src={pdfUrl} />
 */
export function useConsentPdf(
  patientId: string | null | undefined,
  consentId: string | null | undefined,
) {
  return useQuery({
    queryKey: ["consents", patientId, consentId, "pdf"],
    queryFn: async () => {
      const response = await apiClient.get(
        `/patients/${patientId}/consents/${consentId}/pdf`,
        { responseType: "blob" },
      );
      const blob = new Blob([response.data as BlobPart], { type: "application/pdf" });
      return URL.createObjectURL(blob);
    },
    enabled: Boolean(patientId) && Boolean(consentId),
    staleTime: 5 * 60_000, // 5 minutes — PDF content doesn't change once signed
    gcTime: 10 * 60_000,   // Release the object URL after 10 minutes
  });
}
