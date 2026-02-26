"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export type NotificationType =
  | "appointment_reminder"
  | "appointment_confirmed"
  | "appointment_cancelled"
  | "new_patient"
  | "payment_received"
  | "payment_overdue"
  | "treatment_plan_approved"
  | "consent_signed"
  | "message_received"
  | "inventory_alert"
  | "system_update";

export interface NotificationResponse {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
  meta_data: {
    resource_type?: string;
    resource_id?: string;
    action_url?: string;
  };
}

export interface NotificationPagination {
  next_cursor: string | null;
  has_more: boolean;
  total_unread: number;
}

export interface NotificationListResponse {
  data: NotificationResponse[];
  pagination: NotificationPagination;
}

export interface PreferenceChannel {
  email: boolean;
  sms: boolean;
  whatsapp: boolean;
  in_app: true;
}

export interface NotificationPreferenceResponse {
  preferences: Record<string, PreferenceChannel>;
}

export interface PreferenceUpdate {
  event_type: string;
  channel: string;
  enabled: boolean;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const NOTIFICATIONS_KEY = ["notifications"] as const;
export const NOTIFICATION_PREFS_KEY = ["notification-preferences"] as const;

// ─── useNotifications ─────────────────────────────────────────────────────────

/**
 * Cursor-paginated infinite query for notifications.
 */
export function useNotifications(
  status?: "read" | "unread" | "all",
  type?: NotificationType,
) {
  const params = new URLSearchParams();
  if (status && status !== "all") params.set("status", status);
  if (type) params.set("type", type);
  params.set("limit", "20");

  return useInfiniteQuery({
    queryKey: [...NOTIFICATIONS_KEY, status ?? "all", type ?? "all"],
    queryFn: async ({ pageParam }: { pageParam?: string }) => {
      const p = new URLSearchParams(params);
      if (pageParam) p.set("cursor", pageParam);
      const qs = p.toString();
      return apiGet<NotificationListResponse>(
        `/notifications${qs ? `?${qs}` : ""}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.pagination.next_cursor ?? undefined,
    staleTime: 30_000,
  });
}

// ─── useUnreadCount ───────────────────────────────────────────────────────────

/**
 * Lightweight polling query for unread notification count.
 * Fetches first page with limit=1 to get total_unread from pagination.
 */
export function useUnreadCount() {
  return useQuery({
    queryKey: [...NOTIFICATIONS_KEY, "unread-count"],
    queryFn: async () => {
      const result = await apiGet<NotificationListResponse>(
        "/notifications?status=unread&limit=1",
      );
      return result.pagination.total_unread;
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

// ─── useMarkRead ──────────────────────────────────────────────────────────────

/**
 * Mutation to mark a single notification as read.
 */
export function useMarkRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) =>
      apiPost<NotificationResponse>(`/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
    },
  });
}

// ─── useMarkAllRead ───────────────────────────────────────────────────────────

/**
 * Mutation to mark all notifications as read.
 */
export function useMarkAllRead() {
  const queryClient = useQueryClient();
  const { success } = useToast();

  return useMutation({
    mutationFn: (typeFilter?: string) =>
      apiPost<{ marked_count: number; type_filter: string | null }>(
        "/notifications/read-all",
        typeFilter ? { type: typeFilter } : {},
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      if (data.marked_count > 0) {
        success(
          "Notificaciones leídas",
          `${data.marked_count} notificación(es) marcada(s) como leída(s).`,
        );
      }
    },
  });
}

// ─── useNotificationPreferences ───────────────────────────────────────────────

/**
 * Query for the user's notification preferences matrix.
 */
export function useNotificationPreferences() {
  return useQuery({
    queryKey: NOTIFICATION_PREFS_KEY,
    queryFn: () =>
      apiGet<NotificationPreferenceResponse>("/notifications/preferences"),
    staleTime: 60_000,
  });
}

// ─── useUpdatePreferences ─────────────────────────────────────────────────────

/**
 * Mutation to update notification preferences.
 */
export function useUpdatePreferences() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (updates: PreferenceUpdate[]) =>
      apiPut<NotificationPreferenceResponse>("/notifications/preferences", {
        preferences: updates,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICATION_PREFS_KEY });
      success("Preferencias guardadas", "Tus preferencias de notificación fueron actualizadas.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudieron guardar las preferencias. Inténtalo de nuevo.";
      error("Error al guardar preferencias", message);
    },
  });
}
