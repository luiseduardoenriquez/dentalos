"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ReferralDashboardStats {
  total_referrals: number;
  successful_referrals: number;
  conversion_rate: number;
  total_rewards_cents: number;
  active_referrers: number;
}

export interface TopReferrer {
  patient_id: string;
  patient_name: string;
  referral_count: number;
  successful_count: number;
  rewards_earned_cents: number;
  conversion_rate: number;
}

export interface ReferralDashboardData {
  stats: ReferralDashboardStats;
  top_referrers: TopReferrer[];
}

export interface PatientReferralSummary {
  referral_code: string | null;
  code_is_active: boolean;
  uses_count: number;
  total_referrals_made: number;
  rewards_pending: number;
  rewards_applied: number;
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useReferralDashboard() {
  return useQuery({
    queryKey: ["referral_dashboard"],
    queryFn: () => apiGet<ReferralDashboardData>("/referral-program/dashboard"),
    staleTime: 60_000,
  });
}

export function usePatientReferralSummary(patientId: string | undefined) {
  return useQuery({
    queryKey: ["referral_patient_summary", patientId],
    queryFn: () =>
      apiGet<PatientReferralSummary>(`/referral-program/patient/${patientId}`),
    enabled: Boolean(patientId),
    staleTime: 120_000,
  });
}
