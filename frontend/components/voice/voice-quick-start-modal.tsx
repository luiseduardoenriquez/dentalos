"use client";

import * as React from "react";
import Link from "next/link";
import { Square, ExternalLink, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { PatientQuickSearch } from "@/components/voice/patient-quick-search";
import { VoiceProcessingStatus } from "@/components/voice/voice-processing-status";
import { TranscriptionReviewPanel } from "@/components/voice/transcription-review-panel";
import { useVoiceOrchestrator } from "@/lib/hooks/use-voice-orchestrator";
import { useVoiceStore } from "@/lib/stores/voice-store";
import type { PatientSearchResult } from "@/lib/hooks/use-patients";
import type { ApplyResponse } from "@/lib/hooks/use-voice";

// ─── Types ────────────────────────────────────────────────────────────────────

interface VoiceQuickStartModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ─── Waveform display ─────────────────────────────────────────────────────────

function WaveformBars({ data }: { data: number[] }) {
  return (
    <div className="flex items-center justify-center gap-0.5 h-10">
      {data.map((value, i) => (
        <div
          key={i}
          className="w-1 rounded-full bg-primary-500 transition-all duration-75"
          style={{ height: `${Math.max(4, value * 40)}px` }}
        />
      ))}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Multi-step modal for the global FAB voice flow.
 * Steps: patient_select -> recording -> processing -> reviewing -> success
 */
export function VoiceQuickStartModal({ open, onOpenChange }: VoiceQuickStartModalProps) {
  const voiceStore = useVoiceStore();
  const phase = voiceStore.phase;

  // Create orchestrator only after patient is selected
  const hasPatient = voiceStore.patient_id !== null;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      if (!isOpen && phase !== "idle" && phase !== "success") {
        // Prevent closing while active — user must cancel explicitly
        return;
      }
      onOpenChange(isOpen);
    }}>
      <DialogContent size="lg" showCloseButton={phase === "idle" || phase === "patient_select" || phase === "success"}>
        {/* Patient selection step */}
        {phase === "patient_select" && (
          <PatientSelectStep />
        )}

        {/* Recording + processing + review steps */}
        {hasPatient && phase !== "patient_select" && phase !== "idle" && (
          <ActiveSessionStep onClose={() => onOpenChange(false)} />
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── Patient Select Step ──────────────────────────────────────────────────────

function PatientSelectStep() {
  const voiceStore = useVoiceStore();

  function handlePatientSelect(patient: PatientSearchResult) {
    voiceStore.set_patient(patient.id, patient.full_name);
    voiceStore.set_phase("recording");
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Dictado por voz</DialogTitle>
        <DialogDescription>
          Seleccione un paciente para iniciar el dictado
        </DialogDescription>
      </DialogHeader>
      <PatientQuickSearch onSelect={handlePatientSelect} />
    </>
  );
}

// ─── Active Session Step (recording -> processing -> review -> success) ──────

function ActiveSessionStep({ onClose }: { onClose: () => void }) {
  const voiceStore = useVoiceStore();

  const orchestrator = useVoiceOrchestrator({
    patient_id: voiceStore.patient_id!,
    context: "odontogram",
    on_session_created: (sid) => {
      voiceStore.set_session(sid);
    },
    on_parse_complete: (results) => {
      voiceStore.set_findings(results.findings, results.warnings, results.filtered_speech);
    },
  });

  // Auto-start recording when this step mounts
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
  }

  function handleRetry() {
    orchestrator.cancel();
    voiceStore.set_phase("recording");
    orchestrator.start_recording();
  }

  function handleDone() {
    voiceStore.reset();
    onClose();
  }

  // Formatted elapsed time
  const formattedTime = React.useMemo(() => {
    const minutes = Math.floor(orchestrator.elapsed_seconds / 60);
    const seconds = orchestrator.elapsed_seconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }, [orchestrator.elapsed_seconds]);

  // ─── Recording ────────────────────────────────────────────────────────

  if (orchestrator.phase === "recording" || orchestrator.phase === "requesting_mic") {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Grabando dictado</DialogTitle>
          <DialogDescription>
            Paciente: {voiceStore.patient_name}
          </DialogDescription>
        </DialogHeader>

        {orchestrator.phase === "requesting_mic" ? (
          <p className="text-sm text-center text-[hsl(var(--muted-foreground))] py-8">
            Solicitando acceso al microfono...
          </p>
        ) : (
          <div className="space-y-6 py-4">
            {/* Pulsing dot + timer */}
            <div className="flex flex-col items-center gap-3">
              <span className="relative flex h-4 w-4">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex h-4 w-4 rounded-full bg-red-500" />
              </span>
              <p className="font-mono text-4xl font-semibold tabular-nums text-foreground">
                {formattedTime}
              </p>
            </div>

            {/* Waveform */}
            <WaveformBars data={orchestrator.frequency_data} />

            {/* Hint */}
            <p className="text-xs text-center text-[hsl(var(--muted-foreground))]">
              Dicte los hallazgos: &quot;Caries en el 36 oclusal, fractura en el 11 incisal...&quot;
            </p>

            {/* Controls */}
            <div className="flex justify-center gap-3">
              <Button variant="outline" onClick={handleCancel}>
                Cancelar
              </Button>
              <Button variant="destructive" onClick={orchestrator.stop_recording}>
                <Square className="mr-2 h-4 w-4" />
                Detener
              </Button>
            </div>
          </div>
        )}
      </>
    );
  }

  // ─── Processing ───────────────────────────────────────────────────────

  if (orchestrator.phase === "stopping" || orchestrator.phase === "processing" || orchestrator.phase === "parsing") {
    const stage =
      orchestrator.phase === "stopping"
        ? "uploading" as const
        : orchestrator.phase === "parsing"
          ? "parsing" as const
          : "transcribing" as const;

    return (
      <>
        <DialogHeader>
          <DialogTitle>Procesando dictado</DialogTitle>
          <DialogDescription>
            Paciente: {voiceStore.patient_name}
          </DialogDescription>
        </DialogHeader>
        <VoiceProcessingStatus stage={stage} />
        <div className="flex justify-center">
          <Button variant="outline" size="sm" onClick={handleCancel}>
            Cancelar
          </Button>
        </div>
      </>
    );
  }

  // ─── Review ───────────────────────────────────────────────────────────

  if (orchestrator.phase === "done" && orchestrator.parse_results && voiceStore.phase !== "success") {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Revision de hallazgos</DialogTitle>
          <DialogDescription>
            Paciente: {voiceStore.patient_name}
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto">
          <TranscriptionReviewPanel
            findings={orchestrator.parse_results.findings}
            warnings={orchestrator.parse_results.warnings}
            filteredSpeech={orchestrator.parse_results.filtered_speech}
            sessionId={orchestrator.session_id!}
            onApplyComplete={handleApplyComplete}
            onCancel={handleCancel}
          />
        </div>
      </>
    );
  }

  // ─── Success ──────────────────────────────────────────────────────────

  if (voiceStore.phase === "success" && voiceStore.apply_result) {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Hallazgos aplicados</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-green-50 p-4 text-center dark:bg-green-900/20">
              <p className="text-2xl font-bold text-green-700 dark:text-green-400">
                {voiceStore.apply_result.applied_count}
              </p>
              <p className="text-sm text-green-600 dark:text-green-500">Aplicados</p>
            </div>
            <div className="rounded-lg bg-yellow-50 p-4 text-center dark:bg-yellow-900/20">
              <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-400">
                {voiceStore.apply_result.skipped_count}
              </p>
              <p className="text-sm text-yellow-600 dark:text-yellow-500">Omitidos</p>
            </div>
          </div>

          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={handleDone}>
              Cerrar
            </Button>
            <Button asChild>
              <Link href={`/patients/${voiceStore.patient_id}/odontogram`}>
                <ExternalLink className="mr-2 h-4 w-4" />
                Ver odontograma
              </Link>
            </Button>
          </div>
        </div>
      </>
    );
  }

  // ─── Error ────────────────────────────────────────────────────────────

  if (orchestrator.phase === "error") {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Error en dictado</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <p className="text-sm text-center text-[hsl(var(--muted-foreground))]">
            {orchestrator.error ?? "Ocurrio un error inesperado."}
          </p>
          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={handleCancel}>
              Cancelar
            </Button>
            <Button onClick={handleRetry}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              Reintentar
            </Button>
          </div>
        </div>
      </>
    );
  }

  return null;
}
