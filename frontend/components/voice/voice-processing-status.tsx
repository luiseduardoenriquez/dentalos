"use client";

import * as React from "react";
import { Loader2, Check, Mic, Brain, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type PipelineStage = "uploading" | "transcribing" | "parsing";

interface VoiceProcessingStatusProps {
  /** Current stage of the processing pipeline */
  stage: PipelineStage;
  className?: string;
}

// ─── Pipeline steps configuration ─────────────────────────────────────────────

const STEPS: { key: PipelineStage; label: string; icon: React.ElementType }[] = [
  { key: "uploading", label: "Subiendo audio", icon: Mic },
  { key: "transcribing", label: "Transcribiendo", icon: FileText },
  { key: "parsing", label: "Analizando hallazgos", icon: Brain },
];

const STAGE_ORDER: Record<PipelineStage, number> = {
  uploading: 0,
  transcribing: 1,
  parsing: 2,
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Animated 3-phase pipeline indicator for voice processing.
 * Shows uploading -> transcribing -> parsing progress.
 */
export function VoiceProcessingStatus({ stage, className }: VoiceProcessingStatusProps) {
  const currentIndex = STAGE_ORDER[stage];

  return (
    <div className={cn("space-y-3 py-4", className)}>
      <p className="text-sm font-medium text-foreground text-center">Procesando dictado...</p>

      <div className="flex items-center justify-center gap-2">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          const isComplete = index < currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <React.Fragment key={step.key}>
              {/* Connector line */}
              {index > 0 && (
                <div
                  className={cn(
                    "h-0.5 w-8 rounded-full transition-colors duration-300",
                    isComplete ? "bg-primary-500" : "bg-[hsl(var(--border))]",
                  )}
                />
              )}

              {/* Step indicator */}
              <div className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-full border-2 transition-all duration-300",
                    isComplete && "border-primary-500 bg-primary-500 text-white",
                    isCurrent && "border-primary-500 bg-primary-50 dark:bg-primary-900/30",
                    !isComplete && !isCurrent && "border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]",
                  )}
                >
                  {isComplete ? (
                    <Check className="h-4 w-4" />
                  ) : isCurrent ? (
                    <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-[10px] whitespace-nowrap",
                    isCurrent ? "text-primary-600 font-medium" : "text-[hsl(var(--muted-foreground))]",
                  )}
                >
                  {step.label}
                </span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
