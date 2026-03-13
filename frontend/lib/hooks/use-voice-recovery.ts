"use client";

import * as React from "react";
import {
  cleanupStaleRecordings,
  getPendingRecordings,
  assembleRecording,
  cleanupRecording,
  updateRecordingStatus,
  updateRecordingSessionId,
  type VoiceRecordingMeta,
} from "@/lib/voice-persistence";
import { useCreateVoiceSession, useUploadAudio } from "@/lib/hooks/use-voice";
import { useToast } from "@/lib/hooks/use-toast";

interface UseVoiceRecoveryReturn {
  pending_recordings: VoiceRecordingMeta[];
  is_loading: boolean;
  retry_upload: (recording: VoiceRecordingMeta) => Promise<void>;
  discard_recording: (recording_id: string) => Promise<void>;
}

export function useVoiceRecovery(): UseVoiceRecoveryReturn {
  const [pendingRecordings, setPendingRecordings] = React.useState<VoiceRecordingMeta[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const { mutateAsync: createSession } = useCreateVoiceSession();
  const { mutateAsync: uploadAudio } = useUploadAudio();
  const { success, error: showError } = useToast();

  // On mount: clean stale recordings and find orphans
  React.useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        await cleanupStaleRecordings();
        const pending = await getPendingRecordings();
        if (!cancelled) {
          setPendingRecordings(pending);
        }
      } catch {
        // IndexedDB unavailable — no recovery possible
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    init();
    return () => { cancelled = true; };
  }, []);

  const retryUpload = React.useCallback(
    async (recording: VoiceRecordingMeta) => {
      try {
        let sessionId = recording.session_id;

        // If no session_id, create one first
        if (!sessionId) {
          const session = await createSession({
            patient_id: recording.patient_id,
            context: recording.context as "odontogram" | "evolution" | "examination",
          });
          sessionId = session.id;
          await updateRecordingSessionId(recording.recording_id, sessionId);
        }

        // Assemble the blob from IDB chunks
        const blob = await assembleRecording(recording.recording_id);
        if (!blob) {
          showError("Error de recuperacion", "No se encontraron datos de audio.");
          await cleanupRecording(recording.recording_id);
          setPendingRecordings((prev) =>
            prev.filter((r) => r.recording_id !== recording.recording_id),
          );
          return;
        }

        // Upload with original idempotency key
        await updateRecordingStatus(recording.recording_id, "uploading");
        await uploadAudio({
          sessionId,
          audioBlob: blob,
          chunkIndex: 0,
          idempotencyKey: recording.idempotency_key,
        });

        // Success — clean up IDB
        await updateRecordingStatus(recording.recording_id, "uploaded");
        await cleanupRecording(recording.recording_id);
        setPendingRecordings((prev) =>
          prev.filter((r) => r.recording_id !== recording.recording_id),
        );
        success("Audio subido", "La grabacion recuperada se subio correctamente.");
      } catch {
        await updateRecordingStatus(
          recording.recording_id,
          "failed",
          "Error al reintentar subida",
        );
        showError("Error al subir", "No se pudo subir la grabacion. Intente de nuevo.");
      }
    },
    [createSession, uploadAudio, success, showError],
  );

  const discardRecording = React.useCallback(async (recording_id: string) => {
    await cleanupRecording(recording_id);
    setPendingRecordings((prev) =>
      prev.filter((r) => r.recording_id !== recording_id),
    );
  }, []);

  return {
    pending_recordings: pendingRecordings,
    is_loading: isLoading,
    retry_upload: retryUpload,
    discard_recording: discardRecording,
  };
}
