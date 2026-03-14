"use client";

/**
 * React Query hooks for AI Radiograph Analysis (AI-01).
 *
 * - useRadiographAnalyses: list analyses for a patient (paginated)
 * - useRadiographAnalysis: single analysis with polling (refetchInterval 3s while processing)
 * - useAnalyzeRadiograph: mutation to trigger analysis
 * - useReviewRadiograph: mutation to review findings
 * - useDeleteRadiograph: mutation to soft-delete
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api-client";

// ── Types ───────────────────────────────────────────────

export interface RadiographFinding {
  tooth_number: string | null;
  finding_type: string;
  severity: string;
  description: string;
  location_detail: string | null;
  confidence: number;
  suggested_action: string | null;
  review_action: string | null;
  review_note: string | null;
}

export interface RadiographAnalysis {
  id: string;
  patient_id: string;
  doctor_id: string;
  document_id: string;
  radiograph_type: string;
  status: "processing" | "completed" | "failed" | "reviewed";
  findings: RadiographFinding[] | null;
  summary: string | null;
  radiograph_quality: string | null;
  recommendations: string | null;
  model_used: string | null;
  input_tokens: number;
  output_tokens: number;
  error_message: string | null;
  reviewed_at: string | null;
  reviewer_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RadiographAnalysisListResponse {
  items: RadiographAnalysis[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnalyzeRequest {
  document_id: string;
  radiograph_type: string;
}

export interface ReviewItem {
  index: number;
  action: "accept" | "reject" | "modify";
  edited_description?: string | null;
}

export interface ReviewRequest {
  items: ReviewItem[];
  reviewer_notes?: string | null;
}

// ── Keys ────────────────────────────────────────────────

const KEYS = {
  all: (patientId: string) => ["radiograph-analyses", patientId] as const,
  detail: (patientId: string, id: string) =>
    ["radiograph-analyses", patientId, id] as const,
};

// ── Hooks ────────────────────────────────────────────────

/**
 * Paginated list of radiograph analyses for a patient.
 *
 * @example
 * const { data, isLoading } = useRadiographAnalyses(patientId);
 */
export function useRadiographAnalyses(
  patientId: string,
  page = 1,
  pageSize = 20,
) {
  return useQuery({
    queryKey: [...KEYS.all(patientId), page, pageSize],
    queryFn: () =>
      apiGet<RadiographAnalysisListResponse>(
        `/patients/${patientId}/radiograph-analyses`,
        { page, page_size: pageSize },
      ),
    enabled: !!patientId,
  });
}

/**
 * Single radiograph analysis by ID.
 * Polls every 3 seconds while the analysis is still processing, then stops.
 *
 * @example
 * const { data: analysis, isLoading } = useRadiographAnalysis(patientId, analysisId);
 */
export function useRadiographAnalysis(patientId: string, id: string) {
  return useQuery({
    queryKey: KEYS.detail(patientId, id),
    queryFn: () =>
      apiGet<RadiographAnalysis>(
        `/patients/${patientId}/radiograph-analyses/${id}`,
      ),
    enabled: !!patientId && !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll every 3s while processing, stop when done
      return data?.status === "processing" ? 3000 : false;
    },
  });
}

/**
 * Mutation to trigger a new AI radiograph analysis for a patient.
 * On success: invalidates the patient's analyses list.
 *
 * @example
 * const { mutate: analyze, isPending } = useAnalyzeRadiograph(patientId);
 * analyze({ document_id: docId, radiograph_type: "panoramic" });
 */
export function useAnalyzeRadiograph(patientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AnalyzeRequest) =>
      apiPost<RadiographAnalysis>(
        `/patients/${patientId}/radiograph-analyses`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEYS.all(patientId) });
    },
  });
}

/**
 * Mutation to review (accept/reject/modify) findings on a completed analysis.
 * On success: invalidates the specific analysis detail and the patient's list.
 *
 * @example
 * const { mutate: review, isPending } = useReviewRadiograph(patientId, analysisId);
 * review({ items: [{ index: 0, action: "accept" }], reviewer_notes: "Confirmed." });
 */
export function useReviewRadiograph(patientId: string, analysisId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ReviewRequest) =>
      apiPut<RadiographAnalysis>(
        `/patients/${patientId}/radiograph-analyses/${analysisId}/review`,
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: KEYS.detail(patientId, analysisId),
      });
      queryClient.invalidateQueries({ queryKey: KEYS.all(patientId) });
    },
  });
}

/**
 * Mutation to soft-delete a radiograph analysis.
 * On success: invalidates the patient's analyses list.
 *
 * @example
 * const { mutate: deleteAnalysis, isPending } = useDeleteRadiograph(patientId);
 * deleteAnalysis(analysisId);
 */
export function useDeleteRadiograph(patientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (analysisId: string) =>
      apiDelete<{ message: string }>(
        `/patients/${patientId}/radiograph-analyses/${analysisId}`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEYS.all(patientId) });
    },
  });
}
