"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { buildQueryString } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface CommissionDoctor {
  id: string;
  name: string;
  specialty: string | null;
}

export interface CommissionEntry {
  doctor: CommissionDoctor;
  procedure_count: number;
  total_revenue: number; // cents
  commission_percentage: number;
  commission_amount: number; // cents
}

export interface CommissionTotals {
  total_revenue: number; // cents
  total_commission: number; // cents
}

export interface CommissionsReportResponse {
  period: { date_from: string; date_to: string };
  currency: string;
  commissions: CommissionEntry[];
  totals: CommissionTotals;
  generated_at: string;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

interface UseCommissionsParams {
  dateFrom: string;
  dateTo: string;
  doctorId?: string | null;
  status?: "paid" | "all";
}

export function useCommissions({
  dateFrom,
  dateTo,
  doctorId,
  status = "paid",
}: UseCommissionsParams) {
  const queryParams: Record<string, unknown> = {
    date_from: dateFrom,
    date_to: dateTo,
    status,
  };
  if (doctorId) queryParams.doctor_id = doctorId;

  return useQuery({
    queryKey: ["commissions", dateFrom, dateTo, doctorId, status],
    queryFn: () =>
      apiGet<CommissionsReportResponse>(
        `/billing/commissions${buildQueryString(queryParams)}`,
      ),
    enabled: Boolean(dateFrom) && Boolean(dateTo),
    staleTime: 60_000,
  });
}
