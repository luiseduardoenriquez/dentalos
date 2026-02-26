"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { portalApiGet, portalApiPost } from "@/lib/portal-api-client";
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

const PORTAL_KEYS = {
  me: ["portal", "me"] as const,
  appointments: ["portal", "appointments"] as const,
  treatmentPlans: ["portal", "treatment-plans"] as const,
  invoices: ["portal", "invoices"] as const,
  documents: ["portal", "documents"] as const,
  messages: ["portal", "messages"] as const,
  odontogram: ["portal", "odontogram"] as const,
};

// ─── usePortalMe ────────────────────────────────────────────────────────────

/**
 * Hydrates portal auth store on mount. Similar to useMe() for dashboard.
 */
export function usePortalMe() {
  const { set_portal_auth, clear_portal_auth, set_loading } =
    usePortalAuthStore();

  const query = useQuery({
    queryKey: PORTAL_KEYS.me,
    queryFn: () => portalApiGet<PortalPatientProfile>("/portal/me"),
    retry: false,
    staleTime: 5 * 60_000,
    enabled: typeof window !== "undefined",
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

// ─── Export types ────────────────────────────────────────────────────────────

export type {
  PortalPatientProfile,
  PortalAppointment,
  PortalTreatmentPlan,
  PortalTreatmentPlanProcedure,
  PortalInvoice,
  PortalDocument,
  PortalMessageThread,
  PortalOdontogram,
};
