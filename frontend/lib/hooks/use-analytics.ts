"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

export type AnalyticsPeriod =
  | "today"
  | "week"
  | "month"
  | "quarter"
  | "year"
  | "custom";

// Shared period info included in every analytics response
export interface PeriodInfo {
  date_from: string;
  date_to: string;
  period: string;
}

// AN-01: Dashboard
export interface PatientStats {
  total: number;
  new_in_period: number;
  growth_percentage: number;
}

export interface AppointmentStats {
  today_count: number;
  period_total: number;
  completed: number;
  cancelled: number;
  no_show_count: number;
  no_show_rate: number;
}

export interface RevenueStats {
  collected: number; // cents
  growth_percentage: number;
  pending_collection: number; // cents
}

export interface TopProcedure {
  cups_code: string;
  description: string;
  count: number;
}

export interface DoctorOccupancy {
  doctor_id: string;
  doctor_name: string;
  completed: number;
  scheduled: number;
  occupancy_rate: number;
}

export interface DashboardResponse {
  period: PeriodInfo;
  patients: PatientStats;
  appointments: AppointmentStats;
  revenue: RevenueStats;
  top_procedures: TopProcedure[];
  doctor_occupancy: DoctorOccupancy[];
}

// AN-02: Patient analytics
export interface DemographicBucket {
  label: string;
  count: number;
}

export interface AcquisitionPoint {
  date: string;
  count: number;
}

export interface PatientAnalyticsResponse {
  period: PeriodInfo;
  demographics_gender: DemographicBucket[];
  demographics_age: DemographicBucket[];
  demographics_city: DemographicBucket[];
  acquisition_trend: AcquisitionPoint[];
  retention_rate: number;
  total_active: number;
  total_inactive: number;
}

// AN-03: Appointment analytics
export interface UtilizationPoint {
  date: string;
  scheduled: number;
  completed: number;
  cancelled: number;
  no_show: number;
}

export interface PeakHour {
  hour: number;
  day_of_week: number;
  count: number;
}

export interface AppointmentAnalyticsResponse {
  period: PeriodInfo;
  utilization: UtilizationPoint[];
  peak_hours: PeakHour[];
  no_show_trend: { date: string; rate: number }[];
  average_duration_minutes: number | null;
}

// AN-04: Revenue analytics
export interface RevenueAnalyticsResponse {
  period: PeriodInfo;
  trend: { date: string; amount: number }[]; // amount in cents
  by_doctor: { doctor_id: string; doctor_name: string; amount: number }[];
  by_procedure: {
    cups_code: string;
    description: string;
    amount: number;
    count: number;
  }[];
  payment_methods: { method: string; amount: number; count: number }[];
  accounts_receivable: number; // cents
}

// AN-07: Audit trail
export interface AuditLogEntry {
  id: string;
  user_id: string;
  user_name: string | null;
  resource_type: string;
  resource_id: string | null;
  action: string;
  changes: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface AuditTrailResponse {
  items: AuditLogEntry[];
  next_cursor: string | null;
  has_more: boolean;
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

const STALE_TIME = 1000 * 60 * 5; // 5 minutes

export function useAnalyticsDashboard(
  period: AnalyticsPeriod,
  dateFrom?: string,
  dateTo?: string,
  doctorId?: string,
) {
  return useQuery<DashboardResponse>({
    queryKey: ["analytics", "dashboard", period, dateFrom, dateTo, doctorId],
    queryFn: () =>
      apiGet<DashboardResponse>("/analytics/dashboard", {
        period,
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
        ...(doctorId && { doctor_id: doctorId }),
      }),
    staleTime: STALE_TIME,
  });
}

export function usePatientAnalytics(
  period: AnalyticsPeriod,
  dateFrom?: string,
  dateTo?: string,
) {
  return useQuery<PatientAnalyticsResponse>({
    queryKey: ["analytics", "patients", period, dateFrom, dateTo],
    queryFn: () =>
      apiGet<PatientAnalyticsResponse>("/analytics/patients", {
        period,
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      }),
    staleTime: STALE_TIME,
  });
}

export function useAppointmentAnalytics(
  period: AnalyticsPeriod,
  dateFrom?: string,
  dateTo?: string,
  doctorId?: string,
) {
  return useQuery<AppointmentAnalyticsResponse>({
    queryKey: [
      "analytics",
      "appointments",
      period,
      dateFrom,
      dateTo,
      doctorId,
    ],
    queryFn: () =>
      apiGet<AppointmentAnalyticsResponse>("/analytics/appointments", {
        period,
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
        ...(doctorId && { doctor_id: doctorId }),
      }),
    staleTime: STALE_TIME,
  });
}

export function useRevenueAnalytics(
  period: AnalyticsPeriod,
  dateFrom?: string,
  dateTo?: string,
  doctorId?: string,
) {
  return useQuery<RevenueAnalyticsResponse>({
    queryKey: ["analytics", "revenue", period, dateFrom, dateTo, doctorId],
    queryFn: () =>
      apiGet<RevenueAnalyticsResponse>("/analytics/revenue", {
        period,
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
        ...(doctorId && { doctor_id: doctorId }),
      }),
    staleTime: STALE_TIME,
  });
}

export function useAuditTrail(
  cursor?: string,
  userId?: string,
  resourceType?: string,
  action?: string,
  dateFrom?: string,
  dateTo?: string,
) {
  return useQuery<AuditTrailResponse>({
    queryKey: [
      "analytics",
      "audit-trail",
      cursor,
      userId,
      resourceType,
      action,
      dateFrom,
      dateTo,
    ],
    queryFn: () =>
      apiGet<AuditTrailResponse>("/analytics/audit-trail", {
        ...(cursor && { cursor }),
        ...(userId && { user_id: userId }),
        ...(resourceType && { resource_type: resourceType }),
        ...(action && { action }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      }),
    staleTime: STALE_TIME,
  });
}
