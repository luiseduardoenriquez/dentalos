"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

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

// AN-08: Workflow compliance
export interface ComplianceViolation {
  patient_id: string;
  reference_type: string;
  reference_id: string;
  days_overdue: number;
}

export interface ComplianceCheck {
  check_key: string;
  check_name: string;
  violation_count: number;
  severity: "high" | "medium" | "low";
  violations: ComplianceViolation[];
}

export interface WorkflowComplianceResponse {
  checks: ComplianceCheck[];
  total_violations: number;
  lookback_days: number;
  ai_narrative: string | null;
}

export function useWorkflowCompliance(
  lookbackDays: number = 30,
  enableAi: boolean = false,
) {
  return useQuery<WorkflowComplianceResponse>({
    queryKey: ["analytics", "workflow-compliance", lookbackDays, enableAi],
    queryFn: () =>
      apiGet<WorkflowComplianceResponse>("/analytics/workflow-compliance", {
        lookback_days: lookbackDays,
        ...(enableAi && { enable_ai: true }),
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

// ─── Analytics Export ────────────────────────────────────────────────────────

export type AnalyticsExportType = "patients" | "appointments" | "revenue";

/**
 * Downloads an analytics CSV export via GET /analytics/export.
 * Uses the raw axios client to get a blob response and triggers a browser download.
 */
export function useAnalyticsExport() {
  const { success, error } = useToast();

  return useMutation({
    mutationFn: async (params: {
      type: AnalyticsExportType;
      format?: string;
      date_from?: string;
      date_to?: string;
    }) => {
      const response = await apiClient.get("/analytics/export", {
        params: {
          type: params.type,
          format: params.format ?? "csv",
          ...(params.date_from && { date_from: params.date_from }),
          ...(params.date_to && { date_to: params.date_to }),
        },
        responseType: "blob",
      });

      const blob = new Blob([response.data], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `dentalos-${params.type}-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      success("Exportación completada", "El archivo CSV se descargó correctamente.");
    },
    onError: () => {
      error("Error al exportar", "No se pudo descargar el archivo. Inténtalo de nuevo.");
    },
  });
}

// ─── AI Token Usage ──────────────────────────────────────────────────────────

export interface AIUsageResponse {
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  period_from: string;
  period_to: string;
}

export function useAITokenUsage() {
  // Backend requires date_from and date_to — default to last 12 months
  const now = new Date();
  const dateTo = now.toISOString().slice(0, 10);
  const dateFrom = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate())
    .toISOString()
    .slice(0, 10);

  return useQuery<AIUsageResponse>({
    queryKey: ["analytics", "ai-usage", dateFrom, dateTo],
    queryFn: () =>
      apiGet<AIUsageResponse>("/treatment-plans/ai-usage", {
        date_from: dateFrom,
        date_to: dateTo,
      }),
    staleTime: STALE_TIME,
  });
}

// ─── Acceptance Rate ─────────────────────────────────────────────────────────

export interface AcceptanceRateResponse {
  total_quotations: number;
  accepted_count: number;
  pending_count: number;
  expired_count: number;
  acceptance_rate: number;
  average_days_to_accept: number | null;
}

export function useAcceptanceRate(dateFrom?: string, dateTo?: string) {
  return useQuery<AcceptanceRateResponse>({
    queryKey: ["analytics", "acceptance-rate", dateFrom, dateTo],
    queryFn: () =>
      apiGet<AcceptanceRateResponse>("/analytics/acceptance-rate", {
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      }),
    staleTime: STALE_TIME,
  });
}

// ─── NPS Survey Dispatch ─────────────────────────────────────────────────────

export interface SendNPSSurveyPayload {
  patient_id: string;
  doctor_id?: string;
  channel: "email" | "whatsapp" | "sms";
}

export interface NPSSurveyResponse {
  id: string;
  patient_id: string;
  doctor_id: string | null;
  channel: string;
  status: string;
  created_at: string;
}

export function useSendNPSSurvey() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: SendNPSSurveyPayload) =>
      apiPost<NPSSurveyResponse>("/surveys/send", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analytics", "nps"] });
      queryClient.invalidateQueries({ queryKey: ["analytics-nps"] });
      success("Encuesta enviada", "La encuesta NPS fue enviada al paciente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo enviar la encuesta. Inténtalo de nuevo.";
      error("Error al enviar encuesta", message);
    },
  });
}
