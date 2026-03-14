"use client";

/**
 * React Query hook for AI Clinical Summary (AI-02).
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";

export interface RiskAlert {
  type: string;
  severity: string;
  message: string;
  recommendation: string;
}

export interface ActiveConditionItem {
  diagnosis: string;
  cie10_code: string | null;
  tooth: string | null;
  severity: string;
  diagnosed_date: string | null;
  relevant_to_today: boolean;
}

export interface PendingTreatmentItem {
  procedure: string;
  cups_code: string | null;
  tooth: string | null;
  status: string;
  estimated_cost_cents: number;
  planned_for_today: boolean;
}

export interface ActionSuggestion {
  priority: string;
  action: string;
  category: string;
}

export interface ClinicalSummarySection {
  title: string;
  content: string;
}

export interface ClinicalSummarySections {
  patient_snapshot: ClinicalSummarySection & { data: Record<string, unknown> };
  today_context: ClinicalSummarySection & { data: Record<string, unknown> };
  active_conditions: ClinicalSummarySection & { items: ActiveConditionItem[] };
  risk_alerts: ClinicalSummarySection & { alerts: RiskAlert[] };
  pending_treatments: ClinicalSummarySection & {
    items: PendingTreatmentItem[];
    total_pending_cost_cents: number;
  };
  last_visit_summary: ClinicalSummarySection & { data: Record<string, unknown> };
  financial_status: ClinicalSummarySection & { data: Record<string, unknown> };
  action_suggestions: ClinicalSummarySection & {
    suggestions: ActionSuggestion[];
  };
}

export interface ClinicalSummaryResponse {
  patient_id: string;
  appointment_id: string | null;
  generated_at: string;
  cached: boolean;
  cached_until: string | null;
  model_used: string | null;
  sections: ClinicalSummarySections;
}

export function useClinicalSummary(
  patientId: string,
  appointmentId?: string | null,
) {
  return useQuery({
    queryKey: ["clinical-summary", patientId, appointmentId ?? "none"],
    queryFn: () => {
      const params: Record<string, unknown> = {};
      if (appointmentId) params.appointment_id = appointmentId;
      return apiGet<ClinicalSummaryResponse>(
        `/patients/${patientId}/clinical-summary`,
        params,
      );
    },
    enabled: !!patientId,
    staleTime: 5 * 60 * 1000, // 5 minutes (matches server cache TTL)
  });
}
