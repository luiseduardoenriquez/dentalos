"use client";

import * as React from "react";
import { Camera, Clock, Loader2, Grid3X3, ArrowUpDown, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { VoiceMicButton } from "@/components/voice/voice-mic-button";
import {
  DENTITION_TYPES,
  DENTITION_LABELS,
  type DentitionType,
} from "@/lib/validations/odontogram";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ViewMode = "classic" | "anatomic";

export interface OdontogramToolbarProps {
  /** Current dentition type selection */
  dentitionType: DentitionType;
  /** Callback when dentition type is changed */
  onDentitionChange: (type: DentitionType) => void;
  /** Callback to create a snapshot of the current odontogram state */
  onSnapshotCreate: () => void;
  /** Callback to open the history panel */
  onHistoryOpen: () => void;
  /** Callback to start voice dictation */
  onVoiceStart?: () => void;
  /** Whether voice dictation is currently active */
  isVoiceActive?: boolean;
  /** Whether any save/mutation is currently in progress */
  isLoading?: boolean;
  /** Whether the toolbar is in read-only mode */
  readOnly?: boolean;
  /** Current view mode (only shown when onViewModeChange is provided) */
  viewMode?: ViewMode;
  /** Callback when view mode changes */
  onViewModeChange?: (mode: ViewMode) => void;
  /** Whether the anatomic view is available for the current plan */
  canUseAnatomic?: boolean;
}

// ─── Dentition Button Labels (short form for toolbar) ─────────────────────────

const SHORT_LABELS: Record<DentitionType, string> = {
  adult: "Adulto",
  pediatric: "Pediatrico",
  mixed: "Mixta",
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Top toolbar for the odontogram view.
 * Contains dentition type selector (3 toggle buttons), snapshot button, and history button.
 */
function OdontogramToolbar({
  dentitionType,
  onDentitionChange,
  onSnapshotCreate,
  onHistoryOpen,
  onVoiceStart,
  isVoiceActive = false,
  isLoading = false,
  readOnly = false,
  viewMode,
  onViewModeChange,
  canUseAnatomic = true,
}: OdontogramToolbarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-3">
        {/* ── Dentition Type Selector ────────────────────────────────── */}
        <div
          className="inline-flex rounded-lg border border-[hsl(var(--border))] p-0.5 bg-[hsl(var(--muted))]"
          role="radiogroup"
          aria-label="Tipo de denticion"
        >
          {DENTITION_TYPES.map((type) => {
            const isActive = dentitionType === type;
            return (
              <button
                key={type}
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => onDentitionChange(type)}
                disabled={readOnly || isLoading}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-md",
                  "transition-all duration-150",
                  isActive
                    ? "bg-[hsl(var(--background))] text-foreground shadow-sm"
                    : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
                  (readOnly || isLoading) && "opacity-50 cursor-not-allowed",
                )}
              >
                {SHORT_LABELS[type]}
              </button>
            );
          })}
        </div>

        {/* ── View Mode Toggle (only when onViewModeChange is provided) ── */}
        {onViewModeChange && viewMode && (
          <div
            className="inline-flex rounded-lg border border-[hsl(var(--border))] p-0.5 bg-[hsl(var(--muted))]"
            role="radiogroup"
            aria-label="Modo de vista"
          >
            <button
              type="button"
              role="radio"
              aria-checked={viewMode === "classic"}
              onClick={() => onViewModeChange("classic")}
              disabled={isLoading}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md",
                "transition-all duration-150",
                viewMode === "classic"
                  ? "bg-[hsl(var(--background))] text-foreground shadow-sm"
                  : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
                isLoading && "opacity-50 cursor-not-allowed",
              )}
            >
              <Grid3X3 className="h-3.5 w-3.5" />
              Grilla
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={viewMode === "anatomic"}
              onClick={() => canUseAnatomic && onViewModeChange("anatomic")}
              disabled={isLoading || !canUseAnatomic}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md",
                "transition-all duration-150",
                viewMode === "anatomic"
                  ? "bg-[hsl(var(--background))] text-foreground shadow-sm"
                  : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
                (isLoading || !canUseAnatomic) && "opacity-50 cursor-not-allowed",
              )}
              title={!canUseAnatomic ? "Vista anatomica disponible en planes Starter+" : undefined}
            >
              <ArrowUpDown className="h-3.5 w-3.5" />
              Arco
              {!canUseAnatomic && <Lock className="h-3 w-3 ml-0.5" />}
            </button>
          </div>
        )}
      </div>

      {/* ── Action Buttons ────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Guardando...</span>
          </div>
        )}

        {/* Snapshot button */}
        {!readOnly && (
          <Button
            variant="outline"
            size="sm"
            onClick={onSnapshotCreate}
            disabled={isLoading}
          >
            <Camera className="mr-1.5 h-3.5 w-3.5" />
            Captura
          </Button>
        )}

        {/* Voice mic button */}
        {!readOnly && onVoiceStart && (
          <VoiceMicButton
            onActivate={onVoiceStart}
            isActive={isVoiceActive}
          />
        )}

        {/* History button */}
        <Button
          variant="outline"
          size="sm"
          onClick={onHistoryOpen}
          disabled={isLoading}
        >
          <Clock className="mr-1.5 h-3.5 w-3.5" />
          Historial
        </Button>
      </div>
    </div>
  );
}

OdontogramToolbar.displayName = "OdontogramToolbar";

export { OdontogramToolbar };
