"use client";

import { useState } from "react";
import { Mic } from "lucide-react";
import { toast } from "sonner";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { SOAPNoteReviewPanel } from "@/components/voice/soap-note-review-panel";

interface DictateClinicalNoteButtonProps {
  patientId: string;
}

interface VoiceSessionResponse {
  id: string;
  status: string;
  context: string;
}

/**
 * Button that creates a voice session (context=evolution), records audio,
 * and triggers SOAP structuring. Lives in the Historial clínico tab.
 *
 * Flow:
 * 1. Click "Dictar nota clínica" → creates voice session
 * 2. Browser starts recording (MediaRecorder API)
 * 3. Click "Detener" → uploads audio → triggers transcription
 * 4. Once transcribed → triggers SOAP structuring
 * 5. Shows SOAPNoteReviewPanel for review + save
 */
export function DictateClinicalNoteButton({
  patientId,
}: DictateClinicalNoteButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [clinicalNoteId, setClinicalNoteId] = useState<string | null>(null);
  const [status, setStatus] = useState<
    "idle" | "recording" | "uploading" | "transcribing" | "structuring" | "review"
  >("idle");
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

  // Create voice session
  const createSession = useMutation({
    mutationFn: () =>
      apiPost<VoiceSessionResponse>("/voice/sessions", {
        patient_id: patientId,
        context: "evolution",
      }),
  });

  // Upload audio chunk
  const uploadAudio = useMutation({
    mutationFn: async ({
      sessionId,
      audioBlob,
    }: {
      sessionId: string;
      audioBlob: Blob;
    }) => {
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");
      const response = await fetch(
        `/api/v1/voice/sessions/${sessionId}/upload`,
        {
          method: "POST",
          body: formData,
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
          },
        },
      );
      if (!response.ok) throw new Error("Upload failed");
      return response.json();
    },
  });

  // Trigger SOAP structuring
  const structureNote = useMutation({
    mutationFn: (sid: string) =>
      apiPost<{ id: string }>(`/voice/sessions/${sid}/structure`, {
        session_id: sid,
      }),
  });

  const handleStartRecording = async () => {
    try {
      // 1. Create voice session
      const session = await createSession.mutateAsync();
      setSessionId(session.id);

      // 2. Start recording
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });

      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const audioBlob = new Blob(chunks, { type: "audio/webm" });

        // 3. Upload audio
        setStatus("uploading");
        try {
          await uploadAudio.mutateAsync({
            sessionId: session.id,
            audioBlob,
          });

          // 4. Wait a moment for transcription, then structure
          setStatus("structuring");
          // Small delay to allow transcription worker to process
          await new Promise((r) => setTimeout(r, 3000));

          const note = await structureNote.mutateAsync(session.id);
          setClinicalNoteId(note.id);
          setStatus("review");
        } catch {
          toast.error("Error al procesar el audio. Intente nuevamente.");
          setStatus("idle");
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setStatus("recording");
    } catch (error: any) {
      if (error?.response?.status === 402) {
        toast.error(
          "El dictado de notas clínicas requiere el add-on AI Voice ($10/doctor/mes).",
          { duration: 5000 },
        );
      } else if (error?.name === "NotAllowedError") {
        toast.error("Permiso de micrófono denegado. Habilítelo en su navegador.");
      } else {
        toast.error("Error al iniciar la grabación.");
      }
      setStatus("idle");
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  // Show SOAP review panel when structuring is done
  if (status === "review" && clinicalNoteId) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">
            Nota clínica dictada
          </h4>
          <button
            onClick={() => {
              setStatus("idle");
              setClinicalNoteId(null);
              setSessionId(null);
            }}
            className="text-xs text-slate-500 hover:text-slate-700"
          >
            Cerrar
          </button>
        </div>
        <SOAPNoteReviewPanel noteId={clinicalNoteId} />
      </div>
    );
  }

  // Processing states
  if (status === "uploading" || status === "structuring") {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 dark:border-primary-800 dark:bg-primary-900/20">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <span className="text-sm text-primary-700 dark:text-primary-300">
          {status === "uploading"
            ? "Subiendo audio..."
            : "Estructurando nota con IA..."}
        </span>
      </div>
    );
  }

  // Recording state
  if (status === "recording") {
    return (
      <button
        onClick={handleStopRecording}
        className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
      >
        <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
        Detener grabación
      </button>
    );
  }

  // Idle state — show button
  return (
    <button
      onClick={handleStartRecording}
      disabled={createSession.isPending}
      className="inline-flex items-center gap-1.5 rounded-md border border-primary-300 bg-primary-50 px-3 py-1.5 text-sm font-medium text-primary-700 hover:bg-primary-100 disabled:opacity-50 dark:border-primary-700 dark:bg-primary-900/20 dark:text-primary-300 dark:hover:bg-primary-900/40"
    >
      <Mic className="h-3.5 w-3.5" />
      Dictar nota clínica
    </button>
  );
}
