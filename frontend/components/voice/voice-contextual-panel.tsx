"use client";

import * as React from "react";
import { Mic, Square, X, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { VoiceProcessingStatus } from "@/components/voice/voice-processing-status";
import { TranscriptionReviewPanel } from "@/components/voice/transcription-review-panel";
import { useVoiceOrchestrator } from "@/lib/hooks/use-voice-orchestrator";
import { useVoiceStore } from "@/lib/stores/voice-store";
import { cn } from "@/lib/utils";
import type { ApplyResponse } from "@/lib/hooks/use-voice";

// ─── Types ────────────────────────────────────────────────────────────────────

interface VoiceContextualPanelProps {
  patient_id: string;
  patient_name: string;
  /** Called when the voice session is finished (apply or cancel) */
  onClose: () => void;
  className?: string;
}

// ─── Waveform display ─────────────────────────────────────────────────────────

function WaveformBars({ data }: { data: number[] }) {
  return (
    <div className="flex items-center justify-center gap-0.5 h-8">
      {data.map((value, i) => (
        <div
          key={i}
          className="w-1 rounded-full bg-primary-500 transition-all duration-75"
          style={{ height: `${Math.max(4, value * 32)}px` }}
        />
      ))}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Sidebar voice panel for the odontogram contextual flow.
 * Orchestrates: recording -> processing -> review -> apply.
 */
export function VoiceContextualPanel({
  patient_id,
  patient_name,
  onClose,
  className,
}: VoiceContextualPanelProps) {
  const voiceStore = useVoiceStore();

  const orchestrator = useVoiceOrchestrator({
    patient_id,
    context: "odontogram",
    on_session_created: (sid) => {
      voiceStore.set_session(sid);
    },
    on_parse_complete: (results) => {
      voiceStore.set_findings(results.findings, results.warnings, results.filtered_speech);
    },
  });

  // Auto-start recording on mount
  React.useEffect(() => {
    if (orchestrator.phase === "idle") {
      orchestrator.start_recording();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleCancel() {
    orchestrator.cancel();
    voiceStore.reset();
    onClose();
  }

  function handleApplyComplete(result: ApplyResponse) {
    voiceStore.set_apply_result(result);
    // Auto-close after brief delay so user sees the success
    setTimeout(() => {
      voiceStore.reset();
      onClose();
    }, 2000);
  }

  function handleRetry() {
    orchestrator.cancel();
    voiceStore.set_phase("recording");
    orchestrator.start_recording();
  }

  // ─── Formatted elapsed time ─────────────────────────────────────────────

  const formattedTime = React.useMemo(() => {
    const minutes = Math.floor(orchestrator.elapsed_seconds / 60);
    const seconds = orchestrator.elapsed_seconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }, [orchestrator.elapsed_seconds]);

  // ─── Render: Recording ──────────────────────────────────────────────────

  if (orchestrator.phase === "recording" || orchestrator.phase === "requesting_mic") {
    return (
      <Card className={cn("", className)}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
              </span>
              Dictado de voz
            </CardTitle>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCancel} title="Cancelar">
              <X className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Paciente: {patient_name}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {orchestrator.phase === "requesting_mic" ? (
            <p className="text-sm text-center text-[hsl(var(--muted-foreground))] py-4">
              Solicitando acceso al microfono...
            </p>
          ) : (
            <>
              {/* Timer */}
              <p className="text-center font-mono text-2xl font-semibold tabular-nums text-foreground">
                {formattedTime}
              </p>

              {/* Waveform */}
              <WaveformBars data={orchestrator.frequency_data} />

              {/* Hint */}
              <p className="text-xs text-center text-[hsl(var(--muted-foreground))]">
                Dicte los hallazgos: &quot;Caries en el 36 oclusal...&quot;
              </p>

              {/* Stop button */}
              <Button
                variant="destructive"
                className="w-full"
                onClick={orchestrator.stop_recording}
              >
                <Square className="mr-2 h-4 w-4" />
                Detener
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    );
  }

  // ─── Render: Processing ─────────────────────────────────────────────────

  if (orchestrator.phase === "stopping" || orchestrator.phase === "processing" || orchestrator.phase === "parsing") {
    const stage =
      orchestrator.phase === "stopping"
        ? "uploading" as const
        : orchestrator.phase === "parsing"
          ? "parsing" as const
          : "transcribing" as const;

    return (
      <Card className={cn("", className)}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Procesando dictado</CardTitle>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCancel} title="Cancelar">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <VoiceProcessingStatus stage={stage} />
        </CardContent>
      </Card>
    );
  }

  // ─── Render: Review ─────────────────────────────────────────────────────

  if (orchestrator.phase === "done" && orchestrator.parse_results) {
    return (
      <TranscriptionReviewPanel
        findings={orchestrator.parse_results.findings}
        warnings={orchestrator.parse_results.warnings}
        filteredSpeech={orchestrator.parse_results.filtered_speech}
        sessionId={orchestrator.session_id!}
        onApplyComplete={handleApplyComplete}
        onCancel={handleCancel}
        compact
      />
    );
  }

  // ─── Render: Error ──────────────────────────────────────────────────────

  if (orchestrator.phase === "error") {
    return (
      <Card className={cn("", className)}>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Error en dictado</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {orchestrator.error ?? "Ocurrio un error inesperado."}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCancel}>
              Cancelar
            </Button>
            <Button size="sm" onClick={handleRetry}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              Reintentar
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ─── Render: Success (brief, auto-closes) ──────────────────────────────

  if (voiceStore.phase === "success" && voiceStore.apply_result) {
    return (
      <Card className={cn("", className)}>
        <CardContent className="py-6 text-center space-y-2">
          <p className="text-sm font-medium text-green-700 dark:text-green-400">
            {voiceStore.apply_result.applied_count} hallazgo
            {voiceStore.apply_result.applied_count !== 1 ? "s" : ""} aplicado
            {voiceStore.apply_result.applied_count !== 1 ? "s" : ""}
          </p>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Cerrando...</p>
        </CardContent>
      </Card>
    );
  }

  return null;
}
