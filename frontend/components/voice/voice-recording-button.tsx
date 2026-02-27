"use client";

import * as React from "react";
import { Mic, MicOff, Square, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVoiceOrchestrator } from "@/lib/hooks/use-voice-orchestrator";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface VoiceRecordingButtonProps {
  /** Patient ID for session creation */
  patientId: string;
  /** Callback fired after recording stops and parse results are ready */
  onParseComplete?: (results: { findings: unknown[]; warnings: string[]; filtered_speech: string[] }) => void;
  /** Additional CSS class for the container */
  className?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const WAVEFORM_BAR_COUNT = 16;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Floating action button for voice recording.
 * Uses the shared useVoiceOrchestrator hook for all recording logic.
 *
 * Positioned fixed at the bottom-right of the viewport.
 */
export function VoiceRecordingButton({
  patientId,
  onParseComplete,
  className,
}: VoiceRecordingButtonProps) {
  const orchestrator = useVoiceOrchestrator({
    patient_id: patientId,
    context: "odontogram",
    on_parse_complete: onParseComplete,
  });

  const { phase, elapsed_seconds, frequency_data, is_media_recorder_supported } = orchestrator;

  // ─── Formatted elapsed time ─────────────────────────────────────────────

  const formattedTime = React.useMemo(() => {
    const minutes = Math.floor(elapsed_seconds / 60);
    const seconds = elapsed_seconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }, [elapsed_seconds]);

  // ─── Click handler ──────────────────────────────────────────────────────

  function handleClick() {
    if (phase === "recording") {
      orchestrator.stop_recording();
    } else if (phase === "idle" || phase === "done") {
      orchestrator.start_recording();
    }
  }

  // ─── Derived state ─────────────────────────────────────────────────────

  const isDisabled = !is_media_recorder_supported || phase === "stopping" || phase === "processing" || phase === "parsing";
  const isRecording = phase === "recording";
  const isProcessing = phase === "stopping" || phase === "processing" || phase === "parsing";

  // ─── Render ─────────────────────────────────────────────────────────────

  return (
    <div className={cn("fixed bottom-6 right-6 z-50 flex flex-col items-center gap-2", className)}>
      {/* Recording indicator: elapsed time + waveform */}
      {isRecording && (
        <div className="flex items-center gap-3 rounded-full bg-[hsl(var(--card))] px-4 py-2 shadow-lg border border-[hsl(var(--border))]">
          {/* Pulsing red dot */}
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" />
          </span>

          {/* Elapsed time */}
          <span className="text-sm font-mono font-medium tabular-nums text-foreground">
            {formattedTime}
          </span>

          {/* Waveform bars */}
          <div className="flex items-center gap-0.5 h-6">
            {frequency_data.map((value, i) => (
              <div
                key={i}
                className="w-0.5 rounded-full bg-primary-500 transition-all duration-75"
                style={{ height: `${Math.max(4, value * 24)}px` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Processing indicator */}
      {isProcessing && (
        <div className="flex items-center gap-2 rounded-full bg-[hsl(var(--card))] px-4 py-2 shadow-lg border border-[hsl(var(--border))]">
          <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
          <span className="text-sm text-[hsl(var(--muted-foreground))]">Procesando...</span>
        </div>
      )}

      {/* Main FAB button */}
      <Button
        variant={isRecording ? "destructive" : "default"}
        size="icon"
        className={cn(
          "h-14 w-14 rounded-full shadow-lg",
          isRecording && "animate-pulse",
        )}
        disabled={isDisabled}
        onClick={handleClick}
        title={
          isRecording
            ? "Detener grabacion"
            : "Iniciar grabacion"
        }
      >
        {isProcessing ? (
          <Loader2 className="h-6 w-6 animate-spin" />
        ) : isRecording ? (
          <Square className="h-6 w-6" />
        ) : !is_media_recorder_supported ? (
          <MicOff className="h-6 w-6" />
        ) : (
          <Mic className="h-6 w-6" />
        )}
      </Button>
    </div>
  );
}
