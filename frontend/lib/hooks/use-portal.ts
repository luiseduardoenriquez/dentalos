"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  portalApiGet,
  portalApiPost,
  portalApiPut,
  portalApiUpload,
} from "@/lib/portal-api-client";
import { usePortalAuthStore } from "@/lib/stores/portal-auth-store";
import { useEffect } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CursorPagination {
  next_cursor: string | null;
  has_more: boolean;
}

interface PortalPatientProfile {
  id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  birthdate: string | null;
  gender: string | null;
  document_type: string;
  document_number: string;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  insurance_provider: string | null;
  insurance_policy_number: string | null;
  clinic: {
    name: string;
    slug: string;
    logo_url: string | null;
    phone: string | null;
    address: string | null;
  };
  outstanding_balance: number;
  unread_messages: number;
  next_appointment: PortalAppointment | null;
}

interface PortalAppointment {
  id: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  appointment_type: string | null;
  doctor_name: string;
  doctor_specialty: string | null;
  notes_for_patient: string | null;
}

interface PortalAppointmentList {
  data: PortalAppointment[];
  pagination: CursorPagination;
}

interface PortalTreatmentPlanProcedure {
  id: string;
  name: string;
  status: string;
  cost: number;
  tooth_number: string | null;
}

interface PortalTreatmentPlan {
  id: string;
  name: string;
  status: string;
  procedures: PortalTreatmentPlanProcedure[];
  total: number;
  paid: number;
  progress_pct: number;
  created_at: string;
}

interface PortalTreatmentPlanList {
  data: PortalTreatmentPlan[];
  pagination: CursorPagination;
}

interface PortalInvoice {
  id: string;
  invoice_number: string | null;
  date: string;
  total: number;
  paid: number;
  balance: number;
  status: string;
  line_items: {
    description: string;
    quantity: number;
    unit_price: number;
    total: number;
  }[];
}

interface PortalInvoiceList {
  data: PortalInvoice[];
  pagination: CursorPagination;
}

interface PortalDocument {
  id: string;
  document_type: string;
  name: string;
  created_at: string;
  signed_at: string | null;
  url: string | null;
}

interface PortalDocumentList {
  data: PortalDocument[];
  pagination: CursorPagination;
}

interface PortalMessageThread {
  id: string;
  subject: string | null;
  last_message_at: string;
  unread_count: number;
  messages: {
    id: string;
    body: string;
    sender_type: "patient" | "staff";
    sender_name: string;
    created_at: string;
  }[];
}

interface PortalMessageList {
  data: PortalMessageThread[];
  pagination: CursorPagination;
}

interface PortalOdontogram {
  teeth: {
    tooth_number: string;
    conditions: {
      condition_code: string;
      condition_name: string;
      surface: string | null;
      description: string | null;
    }[];
    status: string | null;
  }[];
  last_updated: string | null;
  legend: Record<string, string>;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

interface PortalPostopInstruction {
  id: string;
  procedure_type: string;
  title: string;
  instruction_content: string;
  channel: string;
  doctor_name: string | null;
  sent_at: string;
  is_read: boolean;
  read_at: string | null;
}

interface PortalPostopList {
  data: PortalPostopInstruction[];
  pagination: CursorPagination;
}

interface NotificationPreferences {
  email_enabled: boolean;
  whatsapp_enabled: boolean;
  sms_enabled: boolean;
  appointment_reminders: boolean;
  treatment_updates: boolean;
  billing_notifications: boolean;
  marketing_messages: boolean;
}

interface OdontogramSnapshot {
  id: string;
  snapshot_date: string;
  tooth_count: number;
  condition_count: number;
  notes: string | null;
}

// ─── Phase 2 Types ──────────────────────────────────────────────────────────

interface PortalMembership {
  has_membership: boolean;
  subscription: {
    id: string;
    plan_name: string;
    status: string;
    billing_date: string | null;
    benefits: string[];
  } | null;
}

interface PortalSurveyResponse {
  id: string;
  nps_score: number | null;
  csat_score: number | null;
  comments: string | null;
  channel_sent: string;
  sent_at: string;
  responded_at: string | null;
}

interface PortalFinancingApp {
  id: string;
  provider: string;
  status: string;
  amount_cents: number;
  installments: number;
  created_at: string;
}

interface PortalFamilyMember {
  id: string;
  first_name: string;
  last_name: string;
  relationship: string;
}

interface PortalFamilyGroup {
  id: string;
  name: string;
  members: PortalFamilyMember[];
  total_outstanding: number;
}

interface PortalLabOrder {
  id: string;
  order_type: string;
  status: string;
  due_date: string | null;
  lab_name: string | null;
  created_at: string;
}

interface PortalToothPhoto {
  id: string;
  tooth_number: number;
  url: string;
  thumbnail_url: string | null;
  created_at: string;
}

interface PortalHealthHistory {
  allergies: string[];
  medications: string[];
  conditions: string[];
  surgeries: string[];
  notes: string | null;
}

interface FinancingSimulationOption {
  installments: number;
  monthly_payment_cents: number;
  total_cents: number;
  interest_rate_pct: number;
}

interface FinancingSimulationResult {
  provider: string;
  eligible: boolean;
  options: FinancingSimulationOption[];
  message: string | null;
}

interface PortalTimelineEvent {
  id: string;
  event_type: string;
  title: string;
  date: string;
  status: string | null;
  photo_url: string | null;
  tooth_number: string | null;
  treatment_plan_name: string | null;
}

const PORTAL_KEYS = {
  me: ["portal", "me"] as const,
  appointments: ["portal", "appointments"] as const,
  treatmentPlans: ["portal", "treatment-plans"] as const,
  invoices: ["portal", "invoices"] as const,
  documents: ["portal", "documents"] as const,
  messages: ["portal", "messages"] as const,
  odontogram: ["portal", "odontogram"] as const,
  odontogramHistory: ["portal", "odontogram", "history"] as const,
  postop: ["portal", "postop"] as const,
  notificationPrefs: ["portal", "notification-preferences"] as const,
  membership: ["portal", "membership"] as const,
  surveys: ["portal", "surveys"] as const,
  financing: ["portal", "financing"] as const,
  family: ["portal", "family"] as const,
  labOrders: ["portal", "lab-orders"] as const,
  photos: ["portal", "photos"] as const,
  healthHistory: ["portal", "health-history"] as const,
  intakeForm: ["portal", "intake-form"] as const,
  timeline: ["portal", "timeline"] as const,
};

// ─── usePortalMe ────────────────────────────────────────────────────────────

/**
 * Hydrates portal auth store on mount. Similar to useMe() for dashboard.
 */
export function usePortalMe(enabled = true) {
  const { set_portal_auth, clear_portal_auth, set_loading } =
    usePortalAuthStore();

  const query = useQuery({
    queryKey: PORTAL_KEYS.me,
    queryFn: () => portalApiGet<PortalPatientProfile>("/portal/me"),
    retry: false,
    staleTime: 5 * 60_000,
    enabled: enabled && typeof window !== "undefined",
  });

  useEffect(() => {
    if (query.data) {
      set_portal_auth(
        {
          id: query.data.id,
          first_name: query.data.first_name,
          last_name: query.data.last_name,
          email: query.data.email,
          phone: query.data.phone,
        },
        query.data.clinic
          ? {
              slug: query.data.clinic.slug,
              name: query.data.clinic.name,
              logo_url: query.data.clinic.logo_url,
              primary_color: null,
            }
          : null,
      );
    }
    if (query.error) {
      clear_portal_auth();
    }
    if (!query.isLoading && !query.data && !query.error) {
      set_loading(false);
    }
  }, [query.data, query.error, query.isLoading]);

  return query;
}

// ─── Data Hooks ─────────────────────────────────────────────────────────────

export function usePortalAppointments(
  view?: "upcoming" | "past" | "all",
  status?: string,
) {
  const params = new URLSearchParams();
  if (view && view !== "all") params.set("view", view);
  if (status) params.set("status", status);
  params.set("limit", "20");

  return useInfiniteQuery({
    queryKey: [...PORTAL_KEYS.appointments, view ?? "all", status ?? "all"],
    queryFn: async ({ pageParam }: { pageParam?: string }) => {
      const p = new URLSearchParams(params);
      if (pageParam) p.set("cursor", pageParam);
      return portalApiGet<PortalAppointmentList>(
        `/portal/appointments?${p.toString()}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.next_cursor ?? undefined,
    staleTime: 30_000,
  });
}

export function usePortalTreatmentPlans() {
  return useInfiniteQuery({
    queryKey: PORTAL_KEYS.treatmentPlans,
    queryFn: async ({ pageParam }: { pageParam?: string }) => {
      const params = new URLSearchParams({ limit: "20" });
      if (pageParam) params.set("cursor", pageParam);
      return portalApiGet<PortalTreatmentPlanList>(
        `/portal/treatment-plans?${params.toString()}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.next_cursor ?? undefined,
    staleTime: 60_000,
  });
}

export function usePortalInvoices() {
  return useInfiniteQuery({
    queryKey: PORTAL_KEYS.invoices,
    queryFn: async ({ pageParam }: { pageParam?: string }) => {
      const params = new URLSearchParams({ limit: "20" });
      if (pageParam) params.set("cursor", pageParam);
      return portalApiGet<PortalInvoiceList>(
        `/portal/invoices?${params.toString()}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.next_cursor ?? undefined,
    staleTime: 60_000,
  });
}

export function usePortalDocuments(type?: string) {
  return useInfiniteQuery({
    queryKey: [...PORTAL_KEYS.documents, type ?? "all"],
    queryFn: async ({ pageParam }: { pageParam?: string }) => {
      const params = new URLSearchParams({ limit: "20" });
      if (type) params.set("doc_type", type);
      if (pageParam) params.set("cursor", pageParam);
      return portalApiGet<PortalDocumentList>(
        `/portal/documents?${params.toString()}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.next_cursor ?? undefined,
    staleTime: 60_000,
  });
}

export function usePortalMessages() {
  return useInfiniteQuery({
    queryKey: PORTAL_KEYS.messages,
    queryFn: async ({ pageParam }: { pageParam?: string }) => {
      const params = new URLSearchParams({ limit: "20" });
      if (pageParam) params.set("cursor", pageParam);
      return portalApiGet<PortalMessageList>(
        `/portal/messages?${params.toString()}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.next_cursor ?? undefined,
    staleTime: 30_000,
  });
}

export function usePortalOdontogram() {
  return useQuery({
    queryKey: PORTAL_KEYS.odontogram,
    queryFn: () => portalApiGet<PortalOdontogram>("/portal/odontogram"),
    staleTime: 5 * 60_000,
  });
}

// ─── Mutation Hooks ─────────────────────────────────────────────────────────

export function usePortalBookAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      doctor_id: string;
      appointment_type_id: string;
      preferred_date: string;
      preferred_time: string;
      notes?: string;
    }) => portalApiPost<{ id: string; message: string }>("/portal/appointments", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.appointments });
    },
  });
}

export function usePortalCancelAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      appointmentId,
      reason,
    }: {
      appointmentId: string;
      reason?: string;
    }) =>
      portalApiPost<{ id: string; message: string }>(
        `/portal/appointments/${appointmentId}/cancel`,
        { reason },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.appointments });
    },
  });
}

export function usePortalApprovePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      planId,
      signature_data,
      agreed_terms,
    }: {
      planId: string;
      signature_data: string;
      agreed_terms: boolean;
    }) =>
      portalApiPost<{ id: string; message: string }>(
        `/portal/treatment-plans/${planId}/approve`,
        { signature_data, agreed_terms },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.treatmentPlans });
    },
  });
}

export function usePortalSignConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      consentId,
      signature_data,
      acknowledged,
    }: {
      consentId: string;
      signature_data: string;
      acknowledged: boolean;
    }) =>
      portalApiPost<{ id: string; message: string }>(
        `/portal/consents/${consentId}/sign`,
        { signature_data, acknowledged },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.documents });
    },
  });
}

export function usePortalSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      thread_id?: string;
      body: string;
      attachment_ids?: string[];
    }) => portalApiPost<{ id: string; message: string }>("/portal/messages", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.messages });
    },
  });
}

// ─── Postop Hook (G1) ───────────────────────────────────────────────────────

export function usePortalPostop() {
  return useInfiniteQuery({
    queryKey: PORTAL_KEYS.postop,
    queryFn: async ({ pageParam }: { pageParam?: string }) => {
      const params = new URLSearchParams({ limit: "20" });
      if (pageParam) params.set("cursor", pageParam);
      return portalApiGet<PortalPostopList>(
        `/portal/postop?${params.toString()}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.pagination.next_cursor ?? undefined,
    staleTime: 60_000,
  });
}

// ─── Profile Update Hook (V1) ───────────────────────────────────────────────

export function usePortalUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      phone?: string;
      email?: string;
      address?: string;
      emergency_contact_name?: string;
      emergency_contact_phone?: string;
    }) => portalApiPut<{ message: string }>("/portal/me", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.me });
    },
  });
}

// ─── Notification Preferences Hooks (V2) ────────────────────────────────────

export function usePortalNotificationPrefs() {
  return useQuery({
    queryKey: PORTAL_KEYS.notificationPrefs,
    queryFn: () =>
      portalApiGet<NotificationPreferences>("/portal/notifications/preferences"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalUpdateNotificationPrefs() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<NotificationPreferences>) =>
      portalApiPut<NotificationPreferences & { message: string }>(
        "/portal/notifications/preferences",
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.notificationPrefs });
    },
  });
}

// ─── Reschedule Hook (V3) ───────────────────────────────────────────────────

export function usePortalRescheduleAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      appointmentId,
      new_date,
      new_time,
    }: {
      appointmentId: string;
      new_date: string;
      new_time: string;
    }) =>
      portalApiPost<{ id: string; message: string }>(
        `/portal/appointments/${appointmentId}/reschedule`,
        { new_date, new_time },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.appointments });
    },
  });
}

// ─── Document Upload Hook (V4) ──────────────────────────────────────────────

export function usePortalUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      docType,
    }: {
      file: File;
      docType: string;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("doc_type", docType);
      return portalApiUpload<{ id: string; message: string }>(
        "/portal/documents",
        formData,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.documents });
    },
  });
}

// ─── Odontogram History Hook (V5) ───────────────────────────────────────────

export function usePortalOdontogramHistory() {
  return useQuery({
    queryKey: PORTAL_KEYS.odontogramHistory,
    queryFn: () =>
      portalApiGet<{ snapshots: OdontogramSnapshot[] }>("/portal/odontogram/history"),
    staleTime: 5 * 60_000,
  });
}

// ─── Export types ────────────────────────────────────────────────────────────

// ─── Phase 2 Hooks ──────────────────────────────────────────────────────────

export function usePortalMembership() {
  return useQuery({
    queryKey: PORTAL_KEYS.membership,
    queryFn: () => portalApiGet<PortalMembership>("/portal/membership"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalRequestMembershipCancel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { reason?: string }) =>
      portalApiPost<{ message: string }>(
        "/portal/membership/cancel-request",
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.membership });
    },
  });
}

export function usePortalConfirmAttendance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: string) =>
      portalApiPost<{ id: string; message: string }>(
        `/portal/appointments/${appointmentId}/confirm`,
        {},
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.appointments });
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.me });
    },
  });
}

export function usePortalIntakeForm() {
  return useQuery({
    queryKey: PORTAL_KEYS.intakeForm,
    queryFn: () =>
      portalApiGet<{
        form_config: {
          sections: {
            key: string;
            title: string;
            fields: { key: string; label: string; type: string }[];
          }[];
        };
      }>("/portal/intake/form"),
    staleTime: 10 * 60_000,
  });
}

export function usePortalSubmitIntake() {
  return useMutation({
    mutationFn: (data: {
      form_data: Record<string, string>;
      appointment_id?: string;
    }) => portalApiPost<{ message: string }>("/portal/intake", data),
  });
}

export function usePortalSurveys() {
  return useQuery({
    queryKey: PORTAL_KEYS.surveys,
    queryFn: () =>
      portalApiGet<{ data: PortalSurveyResponse[] }>("/portal/surveys"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalFinancing() {
  return useQuery({
    queryKey: PORTAL_KEYS.financing,
    queryFn: () =>
      portalApiGet<{ data: PortalFinancingApp[] }>("/portal/financing"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalSimulateFinancing() {
  return useMutation({
    mutationFn: (data: { amount_cents: number; provider: string }) =>
      portalApiPost<FinancingSimulationResult>(
        "/portal/financing/simulate",
        data,
      ),
  });
}

export function usePortalFamily() {
  return useQuery({
    queryKey: PORTAL_KEYS.family,
    queryFn: () =>
      portalApiGet<{ family: PortalFamilyGroup | null }>("/portal/family"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalLabOrders() {
  return useQuery({
    queryKey: PORTAL_KEYS.labOrders,
    queryFn: () =>
      portalApiGet<{ data: PortalLabOrder[] }>("/portal/lab-orders"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalPhotos() {
  return useQuery({
    queryKey: PORTAL_KEYS.photos,
    queryFn: () =>
      portalApiGet<{ data: PortalToothPhoto[] }>("/portal/photos"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalHealthHistory() {
  return useQuery({
    queryKey: PORTAL_KEYS.healthHistory,
    queryFn: () =>
      portalApiGet<PortalHealthHistory>("/portal/health-history"),
    staleTime: 5 * 60_000,
  });
}

export function usePortalUpdateHealthHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<PortalHealthHistory>) =>
      portalApiPut<{ message: string }>("/portal/health-history", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PORTAL_KEYS.healthHistory });
    },
  });
}

export function usePortalTimeline() {
  return useQuery({
    queryKey: PORTAL_KEYS.timeline,
    queryFn: () =>
      portalApiGet<{ events: PortalTimelineEvent[] }>(
        "/portal/treatment-timeline",
      ),
    staleTime: 5 * 60_000,
  });
}

// ─── Export types ────────────────────────────────────────────────────────

export type {
  PortalPatientProfile,
  PortalAppointment,
  PortalTreatmentPlan,
  PortalTreatmentPlanProcedure,
  PortalInvoice,
  PortalDocument,
  PortalMessageThread,
  PortalOdontogram,
  PortalPostopInstruction,
  NotificationPreferences,
  OdontogramSnapshot,
  PortalMembership,
  PortalSurveyResponse,
  PortalFinancingApp,
  PortalFamilyGroup,
  PortalFamilyMember,
  PortalLabOrder,
  PortalToothPhoto,
  PortalHealthHistory,
  FinancingSimulationResult,
  FinancingSimulationOption,
  PortalTimelineEvent,
};
