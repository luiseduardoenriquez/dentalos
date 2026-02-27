"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useToast } from "@/lib/hooks/use-toast";
import { getApiBaseUrl } from "@/lib/api-base-url";

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE_URL = getApiBaseUrl();

/**
 * Axios instance for unauthenticated public booking requests.
 * No Authorization header, no refresh interceptor — used only for public routes.
 */
const publicClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 30_000,
});

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BookingDoctor {
  id: string;
  full_name: string;
  specialties: string[];
}

export interface BookingAppointmentType {
  type: string;
  label: string;
  duration: number;
}

export interface WorkingHoursBlock {
  start: string;
  end: string;
}

export interface BookingConfig {
  clinic_name: string;
  doctors: BookingDoctor[];
  appointment_types: BookingAppointmentType[];
  /** Day keys: "monday" | "tuesday" | ... | "sunday". null = clinic closed that day. */
  working_hours: Record<string, WorkingHoursBlock | null>;
}

export interface PublicBookingRequest {
  patient_name: string;
  patient_phone: string;
  patient_email?: string | null;
  doctor_id: string;
  appointment_type: string;
  /** ISO datetime string (e.g. "2026-03-15T10:00:00") */
  start_time: string;
  notes?: string | null;
}

export interface PublicBookingResponse {
  appointment_id: string;
  status: string;
  message: string;
  start_time: string;
  doctor_name: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const bookingConfigQueryKey = (slug: string) =>
  ["public", "booking", slug, "config"] as const;

// ─── useBookingConfig ─────────────────────────────────────────────────────────

/**
 * Fetches the public booking configuration for a clinic by its slug.
 * No auth required — uses the unauthenticated public client.
 * Only enabled when slug is a non-empty string.
 *
 * @example
 * const { data: config, isLoading } = useBookingConfig("clinica-nueva-sonrisa");
 */
export function useBookingConfig(slug: string | null | undefined) {
  return useQuery({
    queryKey: bookingConfigQueryKey(slug ?? ""),
    queryFn: async () => {
      const { data } = await publicClient.get<BookingConfig>(
        `/public/booking/${slug}/config`,
      );
      return data;
    },
    enabled: Boolean(slug && slug.trim().length > 0),
    staleTime: 5 * 60 * 1000, // 5 minutes — config rarely changes
  });
}

// ─── useCreatePublicBooking ───────────────────────────────────────────────────

/**
 * POST /public/booking/{slug}/book — submits a public booking request.
 * No auth required — uses the unauthenticated public client.
 * Shows a success or error toast after the mutation settles.
 *
 * @example
 * const { mutate: book, isPending } = useCreatePublicBooking("clinica-nueva-sonrisa");
 * book(formData, { onSuccess: (data) => setConfirmation(data) });
 */
export function useCreatePublicBooking(slug: string) {
  const { success, error } = useToast();

  return useMutation({
    mutationFn: async (payload: PublicBookingRequest): Promise<PublicBookingResponse> => {
      const { data } = await publicClient.post<PublicBookingResponse>(
        `/public/booking/${slug}/book`,
        payload,
      );
      return data;
    },
    onSuccess: (data) => {
      success(
        "Cita solicitada",
        data.message || "Tu solicitud de cita fue recibida correctamente.",
      );
    },
    onError: (err: unknown) => {
      // Detect slot already taken (409 Conflict)
      const axiosErr = err as { response?: { status?: number; data?: { message?: string } } };
      if (axiosErr.response?.status === 409) {
        error(
          "Horario no disponible",
          "El horario seleccionado ya no está disponible. Por favor elige otro.",
        );
        return;
      }
      const message =
        axiosErr.response?.data?.message ??
        (err instanceof Error ? err.message : "No se pudo enviar la solicitud. Inténtalo de nuevo.");
      error("Error al solicitar la cita", message);
    },
  });
}
