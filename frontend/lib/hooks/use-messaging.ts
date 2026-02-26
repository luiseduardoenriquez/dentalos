"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MessageResponse {
  id: string;
  thread_id: string;
  sender_type: "patient" | "staff";
  sender_id: string;
  sender_name: string | null;
  body: string;
  attachments: Record<string, unknown> | null;
  read_at: string | null;
  created_at: string;
}

export interface ThreadResponse {
  id: string;
  patient_id: string;
  subject: string | null;
  status: string;
  created_by: string;
  last_message_at: string;
  unread_count: number;
  created_at: string;
}

interface ThreadPagination {
  next_cursor: string | null;
  has_more: boolean;
}

interface ThreadListResponse {
  data: ThreadResponse[];
  pagination: ThreadPagination;
}

interface MessageListResponse {
  data: MessageResponse[];
  pagination: ThreadPagination;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const MESSAGE_THREADS_KEY = ["message-threads"] as const;
export const threadMessagesKey = (threadId: string) =>
  ["message-threads", threadId, "messages"] as const;

// ─── useMessageThreads ───────────────────────────────────────────────────────

export function useMessageThreads(patientId?: string) {
  return useQuery({
    queryKey: [...MESSAGE_THREADS_KEY, patientId],
    queryFn: () => {
      const params = new URLSearchParams();
      if (patientId) params.set("patient_id", patientId);
      const qs = params.toString();
      return apiGet<ThreadListResponse>(`/messages/threads${qs ? `?${qs}` : ""}`);
    },
    staleTime: 30_000,
  });
}

// ─── useThreadMessages ───────────────────────────────────────────────────────

export function useThreadMessages(threadId: string | null | undefined) {
  return useQuery({
    queryKey: threadMessagesKey(threadId ?? ""),
    queryFn: () =>
      apiGet<MessageListResponse>(`/messages/threads/${threadId}/messages`),
    enabled: Boolean(threadId),
    staleTime: 15_000,
  });
}

// ─── useCreateThread ─────────────────────────────────────────────────────────

export function useCreateThread() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: { patient_id: string; subject?: string; initial_message: string }) =>
      apiPost<ThreadResponse>("/messages/threads", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MESSAGE_THREADS_KEY });
      success("Hilo creado", "El hilo de mensajes fue creado exitosamente.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo crear el hilo. Inténtalo de nuevo.";
      error("Error al crear hilo", message);
    },
  });
}

// ─── useSendMessage ──────────────────────────────────────────────────────────

export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ threadId, body }: { threadId: string; body: string }) =>
      apiPost<MessageResponse>(`/messages/threads/${threadId}/messages`, { body }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: threadMessagesKey(variables.threadId) });
      queryClient.invalidateQueries({ queryKey: MESSAGE_THREADS_KEY });
    },
  });
}

// ─── useMarkThreadRead ───────────────────────────────────────────────────────

export function useMarkThreadRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: string) =>
      apiPost<{ thread_id: string; read_at: string }>(`/messages/threads/${threadId}/read`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MESSAGE_THREADS_KEY });
    },
  });
}
