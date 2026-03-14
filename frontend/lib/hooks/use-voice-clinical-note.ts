"use client";

/**
 * React Query hooks for AI Voice Clinical Notes (AI-03).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";

export interface LinkedCode {
  code: string;
  description: string;
  confidence: number;
}

export interface VoiceClinicalNote {
  id: string;
  session_id: string;
  patient_id: string;
  doctor_id: string;
  status: "processing" | "completed" | "failed" | "saved" | "discarded";
  input_text: string;
  structured_note: {
    subjective?: { title: string; content: string };
    objective?: { title: string; content: string };
    assessment?: { title: string; content: string };
    plan?: { title: string; content: string };
  };
  linked_teeth: number[] | null;
  linked_cie10_codes: LinkedCode[];
  linked_cups_codes: LinkedCode[];
  template_id: string | null;
  model_used: string;
  input_tokens: number;
  output_tokens: number;
  error_message: string | null;
  reviewed_at: string | null;
  clinical_record_id: string | null;
  created_at: string;
  updated_at: string;
}

const KEYS = {
  detail: (noteId: string) => ["voice-clinical-note", noteId] as const,
};

export function useVoiceClinicalNote(noteId: string) {
  return useQuery({
    queryKey: KEYS.detail(noteId),
    queryFn: () =>
      apiGet<VoiceClinicalNote>(`/voice/clinical-notes/${noteId}`),
    enabled: !!noteId,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === "processing" ? 3000 : false;
    },
  });
}

export function useStructureClinicalNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      templateId,
    }: {
      sessionId: string;
      templateId?: string;
    }) =>
      apiPost<VoiceClinicalNote>(
        `/voice/sessions/${sessionId}/structure`,
        {
          session_id: sessionId,
          template_id: templateId ?? null,
        },
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(KEYS.detail(data.id), data);
    },
  });
}

export function useSaveClinicalNote(noteId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (editedNote?: Record<string, unknown>) =>
      apiPost<VoiceClinicalNote>(`/voice/clinical-notes/${noteId}/save`, {
        edited_note: editedNote ?? null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEYS.detail(noteId) });
    },
  });
}
