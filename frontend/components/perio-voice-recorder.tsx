"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Mic, Square, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PerioVoiceRecorderProps {
  patientId: string;
  onTranscriptionComplete?: (transcript: string) => void;
  className?: string;
}

type RecordingPhase = "idle" | "recording" | "processing" | "done" | "error";

// ─── Component ────────────────────────────────────────────────────────────────

export function PerioVoiceRecorder({
  patientId,
  onTranscriptionComplete,
  className,
}: PerioVoiceRecorderProps) {
  const [phase, setPhase] = React.useState<RecordingPhase>("idle");
  const [mediaRecorder, setMediaRecorder] = React.useState<MediaRecorder | null>(null);
  const chunksRef = React.useRef<Blob[]>([]);

  const { mutate: submitAudio, isPending: isSubmitting } = useMutation({
    mutationFn: async (audioBlob: Blob) => {
      const formData = new FormData();
      formData.append("audio", audioBlob, "perio-recording.webm");
      formData.append("patient_id", patientId);
      formData.append("context", "periodontal");
      return apiPost<{ transcript: string }>("/voice/transcribe", formData);
    },
    onSuccess: (data) => {
      setPhase("done");
      onTranscriptionComplete?.(data.transcript);
    },
    onError: () => {
      setPhase("error");
    },
  });

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/ogg",
      });

      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        stream.getTracks().forEach((track) => track.stop());
        setPhase("processing");
        submitAudio(blob);
      };

      recorder.start(100);
      setMediaRecorder(recorder);
      setPhase("recording");
    } catch {
      setPhase("error");
    }
  }

  function stopRecording() {
    mediaRecorder?.stop();
    setMediaRecorder(null);
  }

  function handleClick() {
    if (phase === "recording") {
      stopRecording();
    } else if (phase === "idle" || phase === "done" || phase === "error") {
      setPhase("idle");
      startRecording();
    }
  }

  const isProcessing = phase === "processing" || isSubmitting;
  const isRecording = phase === "recording";
  const isSupported =
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia;

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Main mic button */}
      <Button
        type="button"
        variant={isRecording ? "destructive" : "outline"}
        size="sm"
        disabled={!isSupported || isProcessing}
        onClick={handleClick}
        className={cn(
          "gap-2",
          isRecording && "animate-pulse",
        )}
        title={
          isRecording
            ? "Detener grabación"
            : !isSupported
              ? "Micrófono no disponible"
              : "Iniciar grabación de voz"
        }
      >
        {isProcessing ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Procesando...
          </>
        ) : isRecording ? (
          <>
            <Square className="h-4 w-4" />
            Detener
          </>
        ) : (
          <>
            <Mic className="h-4 w-4" />
            Dictado de voz
          </>
        )}
      </Button>

      {/* Recording state indicator */}
      {isRecording && (
        <div className="flex items-center gap-2 animate-in fade-in-0 duration-200">
          {/* Pulsing red dot */}
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
          </span>
          <span className="text-xs text-red-600 dark:text-red-400 font-medium">
            Escuchando...
          </span>
        </div>
      )}

      {/* Done state */}
      {phase === "done" && !isProcessing && (
        <p className="text-xs text-green-600 dark:text-green-400 animate-in fade-in-0 duration-200">
          Transcripción completada.
        </p>
      )}

      {/* Error state */}
      {phase === "error" && (
        <p className="text-xs text-red-600 dark:text-red-400 animate-in fade-in-0 duration-200">
          Error al procesar el audio.
        </p>
      )}

      {/* Not supported */}
      {!isSupported && (
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Micrófono no disponible en este navegador.
        </p>
      )}
    </div>
  );
}
