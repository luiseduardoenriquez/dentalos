"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { buildQueryString } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface VoiceSession {
  id: string;
  patient_id: string;
  doctor_id: string;
  context: "odontogram" | "evolution" | "general";
  status: "recording" | "processing" | "applied";
  created_at: string;
  expires_at: string;
}

export interface VoiceFinding {
  tooth_number: number; // FDI notation (11-48)
  zone: string | null; // "mesial", "distal", "oclusal", "vestibular", "lingual", "cervical", null for whole tooth
  condition: string; // e.g. "caries", "fractura", "ausente", "corona", "resina"
  confidence: number; // 0.0 to 1.0
  source_text: string; // original text snippet
}

export interface ParseResponse {
  findings: VoiceFinding[];
  filtered_speech: string[];
  warnings: string[];
  corrections: Record<string, string>[];
}

export interface ApplyResponse {
  applied_count: number;
  skipped_count: number;
  details: { tooth_number: number; condition: string; status: string }[];
}

export interface TranscriptionStatus {
  session_id: string;
  transcriptions: {
    id: string;
    chunk_index: number;
    status: "pending" | "processing" | "completed" | "failed";
    text: string | null;
    duration_seconds: number | null;
  }[];
  all_completed: boolean;
}

export interface PaginatedVoiceSessions {
  items: VoiceSession[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const VOICE_SESSIONS_QUERY_KEY = ["voice-sessions"] as const;
export const voiceSessionQueryKey = (id: string) => ["voice-sessions", id] as const;
export const voiceSessionStatusQueryKey = (id: string) =>
  ["voice-sessions", id, "status"] as const;
export const voiceSessionsByPatientQueryKey = (patientId: string) =>
  ["voice-sessions", "patient", patientId] as const;

// ─── useCreateVoiceSession ────────────────────────────────────────────────────

/**
 * POST /voice/sessions — creates a new voice session.
 * On success: invalidates the voice sessions list and shows a success toast.
 *
 * @example
 * const { mutate: createSession, isPending } = useCreateVoiceSession();
 * createSession({ patient_id: "...", context: "odontogram" });
 */
export function useCreateVoiceSession() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: { patient_id: string; context: "odontogram" | "evolution" | "general" }) =>
      apiPost<VoiceSession>("/voice/sessions", data),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: VOICE_SESSIONS_QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: voiceSessionsByPatientQueryKey(session.patient_id),
      });
      success("Sesion de voz iniciada", "Puede comenzar a grabar.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo iniciar la sesion de voz. Intentalo de nuevo.";
      error("Error al iniciar sesion de voz", message);
    },
  });
}

// ─── useUploadAudio ───────────────────────────────────────────────────────────

/**
 * POST /voice/sessions/{id}/upload — uploads an audio chunk via multipart/form-data.
 * Uses apiClient directly to send FormData (bypasses JSON Content-Type header).
 *
 * @example
 * const { mutate: uploadAudio, isPending } = useUploadAudio();
 * uploadAudio({ sessionId: "...", audioBlob: blob, chunkIndex: 0 });
 */
export function useUploadAudio() {
  const { error } = useToast();

  return useMutation({
    mutationFn: async ({
      sessionId,
      audioBlob,
      chunkIndex,
    }: {
      sessionId: string;
      audioBlob: Blob;
      chunkIndex: number;
    }) => {
      const formData = new FormData();
      formData.append("audio", audioBlob, `chunk_${chunkIndex}.webm`);
      formData.append("chunk_index", String(chunkIndex));

      const { data } = await apiClient.post<{ message: string; chunk_index: number }>(
        `/voice/sessions/${sessionId}/upload`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 60_000, // 60s timeout for audio uploads
        },
      );
      return data;
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo subir el audio. Intentalo de nuevo.";
      error("Error al subir audio", message);
    },
  });
}

// ─── useTranscriptionStatus ───────────────────────────────────────────────────

/**
 * GET /voice/sessions/{id}/status — polls transcription status.
 * Refetches every 2 seconds while transcriptions are still processing.
 * Stops polling when all_completed is true or sessionId is null/undefined.
 *
 * @example
 * const { data: status } = useTranscriptionStatus(sessionId);
 * if (status?.all_completed) { // ready to parse }
 */
export function useTranscriptionStatus(sessionId: string | null | undefined) {
  return useQuery({
    queryKey: voiceSessionStatusQueryKey(sessionId ?? ""),
    queryFn: () => apiGet<TranscriptionStatus>(`/voice/sessions/${sessionId}/status`),
    enabled: Boolean(sessionId),
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when all transcriptions are completed or failed
      if (data?.all_completed) return false;
      return 2_000; // Poll every 2 seconds
    },
    staleTime: 0, // Always refetch for real-time status
  });
}

// ─── useParseTranscription ────────────────────────────────────────────────────

/**
 * POST /voice/sessions/{id}/parse — triggers parsing of transcribed audio.
 * Returns structured dental findings extracted from the transcription.
 *
 * @example
 * const { mutate: parse, isPending, data } = useParseTranscription();
 * parse(sessionId);
 */
export function useParseTranscription() {
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (sessionId: string) =>
      apiPost<ParseResponse>(`/voice/sessions/${sessionId}/parse`),
    onSuccess: (data) => {
      const count = data.findings.length;
      success(
        "Transcripcion analizada",
        `Se encontraron ${count} hallazgo${count !== 1 ? "s" : ""} clinico${count !== 1 ? "s" : ""}.`,
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo analizar la transcripcion. Intentalo de nuevo.";
      error("Error al analizar transcripcion", message);
    },
  });
}

// ─── useApplyFindings ─────────────────────────────────────────────────────────

/**
 * POST /voice/sessions/{id}/apply — applies selected findings to the odontogram.
 *
 * @example
 * const { mutate: apply, isPending } = useApplyFindings();
 * apply({ sessionId: "...", findings: selectedFindings });
 */
export function useApplyFindings() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: ({ sessionId, findings }: { sessionId: string; findings: VoiceFinding[] }) =>
      apiPost<ApplyResponse>(`/voice/sessions/${sessionId}/apply`, { findings }),
    onSuccess: (data) => {
      // Invalidate odontogram cache since findings were applied
      queryClient.invalidateQueries({ queryKey: ["odontogram"] });
      queryClient.invalidateQueries({ queryKey: VOICE_SESSIONS_QUERY_KEY });
      success(
        "Hallazgos aplicados",
        `${data.applied_count} aplicado${data.applied_count !== 1 ? "s" : ""}, ${data.skipped_count} omitido${data.skipped_count !== 1 ? "s" : ""}.`,
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudieron aplicar los hallazgos. Intentalo de nuevo.";
      error("Error al aplicar hallazgos", message);
    },
  });
}

// ─── useVoiceSessions ─────────────────────────────────────────────────────────

/**
 * GET /voice/sessions?patient_id={id} — paginated list of past voice sessions for a patient.
 *
 * @example
 * const { data, isLoading } = useVoiceSessions(patientId);
 */
export function useVoiceSessions(
  patientId: string | null | undefined,
  params: { page?: number; page_size?: number } = {},
) {
  const { page = 1, page_size = 20 } = params;

  const queryParams: Record<string, unknown> = {
    patient_id: patientId,
    page,
    page_size,
  };

  return useQuery({
    queryKey: [...voiceSessionsByPatientQueryKey(patientId ?? ""), queryParams],
    queryFn: () =>
      apiGet<PaginatedVoiceSessions>(`/voice/sessions${buildQueryString(queryParams)}`),
    enabled: Boolean(patientId),
    staleTime: 30_000, // 30 seconds
    placeholderData: (previousData) => previousData,
  });
}
