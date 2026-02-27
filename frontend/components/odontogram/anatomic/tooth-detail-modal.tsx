"use client";

import * as React from "react";
import { X, History } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { ToothData, ZoneData, CatalogCondition } from "@/lib/hooks/use-odontogram";
import { isAnteriorTooth, ZONE_LABELS } from "@/lib/validations/odontogram";
import { TOOTH_NAMES_ES } from "@/lib/odontogram/tooth-paths";
import {
  ZONE_POLYGONS,
  EMPTY_FILL_DARK,
  EMPTY_STROKE_DARK,
  CONDITION_STROKE,
  SELECTED_STROKE,
  getZonePositionMap,
  getZoneFill,
  zoneHasCondition,
  type ZonePosition,
} from "@/lib/odontogram/zone-helpers";
import { ZoneChips } from "./zone-chips";
import { ConditionPanel } from "../condition-panel";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ToothDetailModalProps {
  /** FDI tooth number */
  toothNumber: number;
  /** Full tooth data with zone conditions */
  toothData: ToothData;
  /** Conditions catalog for the condition picker */
  conditions: CatalogCondition[];
  /** Callback when a condition is applied */
  onApply: (data: {
    tooth_number: number;
    zone: string;
    condition_code: string;
    severity: string | null;
    notes: string | null;
    source: "manual";
  }) => void;
  /** Callback to close the modal */
  onClose: () => void;
  /** Callback to open history filtered by this tooth */
  onOpenHistory?: (toothNumber: number) => void;
  /** Whether a save is in progress */
  isSaving?: boolean;
  /** Read-only mode */
  readOnly?: boolean;
}

// ─── Zone Diagram (dark theme) ────────────────────────────────────────────────

interface ZoneDiagramProps {
  toothNumber: number;
  zones: ZoneData[];
  selectedZone: string | null;
  onZoneClick: (zone: string) => void;
  readOnly: boolean;
}

function ZoneDiagram({
  toothNumber,
  zones,
  selectedZone,
  onZoneClick,
  readOnly,
}: ZoneDiagramProps) {
  const [hoveredZone, setHoveredZone] = React.useState<string | null>(null);

  const quadrant = Math.floor(toothNumber / 10);
  const isUpper = [1, 2, 5, 6].includes(quadrant);
  const centerZone = isAnteriorTooth(toothNumber) ? "incisal" : "oclusal";
  const zonePositionMap = getZonePositionMap(toothNumber);

  const zonesToRender = React.useMemo(() => {
    const anatomicalZones = isUpper
      ? ["vestibular", "lingual", "mesial", "distal", centerZone, "root"]
      : ["lingual", "vestibular", "mesial", "distal", centerZone, "root"];

    return anatomicalZones
      .filter((z) => zonePositionMap[z] !== undefined)
      .map((zoneName) => ({
        zoneName,
        position: zonePositionMap[zoneName] as ZonePosition,
      }));
  }, [isUpper, centerZone, zonePositionMap]);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg
        width={160}
        height={160}
        viewBox="0 0 56 56"
        xmlns="http://www.w3.org/2000/svg"
        className="drop-shadow-lg"
        aria-label={`Diagrama de zonas — Diente ${toothNumber}`}
        role="img"
      >
        {zonesToRender.map(({ zoneName, position }) => {
          const fill = getZoneFill(zones, zoneName, true);
          const hasCondition = zoneHasCondition(zones, zoneName);
          const isZoneSelected = selectedZone === zoneName;
          const isHovered = hoveredZone === zoneName;

          const stroke = isZoneSelected
            ? SELECTED_STROKE
            : hasCondition
              ? CONDITION_STROKE
              : EMPTY_STROKE_DARK;
          const strokeWidth = isZoneSelected ? 2 : 1;
          const strokeDasharray = isZoneSelected ? "3,2" : undefined;
          const label = ZONE_LABELS[zoneName] ?? zoneName;

          const displayFill =
            isHovered && !readOnly
              ? fill === EMPTY_FILL_DARK
                ? "#4B5563" // slightly lighter on hover
                : fill
              : fill;

          const opacity = isHovered && !readOnly ? 0.8 : 1;

          if (position === "root") {
            return (
              <rect
                key={zoneName}
                x={18}
                y={43}
                width={20}
                height={13}
                fill={displayFill}
                stroke={stroke}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                opacity={opacity}
                className={cn(
                  "transition-all duration-100",
                  !readOnly && "cursor-pointer",
                )}
                onMouseEnter={() => setHoveredZone(zoneName)}
                onMouseLeave={() => setHoveredZone(null)}
                onClick={() => !readOnly && onZoneClick(zoneName)}
                role={readOnly ? undefined : "button"}
                aria-label={label}
                tabIndex={readOnly ? undefined : 0}
                onKeyDown={
                  readOnly
                    ? undefined
                    : (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onZoneClick(zoneName);
                        }
                      }
                }
              />
            );
          }

          const points = ZONE_POLYGONS[position];

          return (
            <polygon
              key={zoneName}
              points={points}
              fill={displayFill}
              stroke={stroke}
              strokeWidth={strokeWidth}
              strokeDasharray={strokeDasharray}
              opacity={opacity}
              className={cn(
                "transition-all duration-100",
                !readOnly && "cursor-pointer",
              )}
              onMouseEnter={() => setHoveredZone(zoneName)}
              onMouseLeave={() => setHoveredZone(null)}
              onClick={() => !readOnly && onZoneClick(zoneName)}
              role={readOnly ? undefined : "button"}
              aria-label={label}
              tabIndex={readOnly ? undefined : 0}
              onKeyDown={
                readOnly
                  ? undefined
                  : (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onZoneClick(zoneName);
                      }
                    }
              }
            />
          );
        })}
      </svg>

      {/* Zone name below diagram */}
      {selectedZone ? (
        <p className="text-xs text-gray-400">
          Zona:{" "}
          <span className="font-medium text-blue-400">
            {ZONE_LABELS[selectedZone] ?? selectedZone}
          </span>
        </p>
      ) : (
        <p className="text-xs text-gray-500">
          Haz clic en una zona para seleccionarla
        </p>
      )}
    </div>
  );
}

// ─── Modal Component ──────────────────────────────────────────────────────────

/**
 * Full-screen modal overlay for tooth detail in anatomic view.
 * Shows a 6-zone interactive diagram, condition picker, zone chips, and notes.
 * Uses dark theme to match the anatomic arch background.
 */
function ToothDetailModal({
  toothNumber,
  toothData,
  conditions,
  onApply,
  onClose,
  onOpenHistory,
  isSaving = false,
  readOnly = false,
}: ToothDetailModalProps) {
  const modalRef = React.useRef<HTMLDivElement>(null);
  const [selectedZone, setSelectedZone] = React.useState<string | null>(null);
  const [selectedCondition, setSelectedCondition] = React.useState<string | null>(null);
  const [severity, setSeverity] = React.useState<string | null>(null);
  const [notes, setNotes] = React.useState("");
  const [isVisible, setIsVisible] = React.useState(false);

  const toothName =
    TOOTH_NAMES_ES[toothNumber] ?? `Diente ${toothNumber}`;

  // Animate in on mount
  React.useEffect(() => {
    requestAnimationFrame(() => setIsVisible(true));
  }, []);

  // Close on Escape
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Focus trap — keep focus inside modal
  React.useEffect(() => {
    const modal = modalRef.current;
    if (!modal) return;

    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    firstFocusable?.focus();

    function trapFocus(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable?.focus();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable?.focus();
        }
      }
    }

    document.addEventListener("keydown", trapFocus);
    return () => document.removeEventListener("keydown", trapFocus);
  }, []);

  const handleZoneClick = React.useCallback((zone: string) => {
    setSelectedZone((prev) => (prev === zone ? null : zone));
    setSelectedCondition(null);
    setSeverity(null);
    setNotes("");
  }, []);

  const handleConditionSelect = React.useCallback(
    (code: string) => {
      setSelectedCondition(selectedCondition === code ? null : code);
      setSeverity(null);
    },
    [selectedCondition],
  );

  const handleApply = React.useCallback(() => {
    if (!selectedZone || !selectedCondition) return;
    onApply({
      tooth_number: toothNumber,
      zone: selectedZone,
      condition_code: selectedCondition,
      severity: severity,
      notes: notes.trim() || null,
      source: "manual",
    });
    // Reset condition selection after apply
    setSelectedCondition(null);
    setSeverity(null);
    setNotes("");
  }, [toothNumber, selectedZone, selectedCondition, severity, notes, onApply]);

  const hasSelection = selectedZone !== null;

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center p-4",
        "transition-opacity duration-200 ease-out",
        isVisible ? "opacity-100" : "opacity-0",
      )}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={`Detalle del diente ${toothNumber}`}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-md"
        aria-hidden="true"
      />

      {/* Modal card */}
      <div
        ref={modalRef}
        className={cn(
          "relative w-full max-w-[640px] max-h-[90vh] overflow-y-auto",
          "rounded-xl border border-gray-700 bg-gray-900 p-6 shadow-2xl",
          "transition-transform duration-200 ease-out",
          isVisible ? "scale-100" : "scale-95",
        )}
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 className="text-lg font-semibold text-white">
              Diente {toothNumber}
            </h2>
            <p className="text-sm text-gray-400 mt-0.5">{toothName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            aria-label="Cerrar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ── Content Grid ───────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-6">
          {/* Left: Zone diagram + chips */}
          <div className="flex flex-col items-center gap-4 shrink-0">
            <ZoneDiagram
              toothNumber={toothNumber}
              zones={toothData.zones}
              selectedZone={selectedZone}
              onZoneClick={handleZoneClick}
              readOnly={readOnly}
            />

            {/* Zone chips */}
            <div className="w-full">
              <p className="text-xs text-gray-500 mb-2 font-medium">
                Hallazgos actuales
              </p>
              <ZoneChips
                zones={toothData.zones}
                onChipClick={readOnly ? undefined : handleZoneClick}
                selectedZone={selectedZone}
              />
            </div>
          </div>

          {/* Right: Condition panel (reuse existing) */}
          {!readOnly && (
            <div className="flex-1 min-w-0">
              <ConditionPanel
                conditions={conditions}
                selectedCondition={selectedCondition}
                onConditionSelect={handleConditionSelect}
                selectedZone={selectedZone}
                severity={severity}
                onSeverityChange={setSeverity}
                notes={notes}
                onNotesChange={setNotes}
                onApply={handleApply}
                isApplying={isSaving}
                hasSelection={hasSelection}
              />
            </div>
          )}

          {/* Read-only message */}
          {readOnly && (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-sm text-gray-500 text-center">
                Solo lectura — no se pueden agregar condiciones.
              </p>
            </div>
          )}
        </div>

        {/* ── Footer Actions ─────────────────────────────────────────── */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-700">
          {onOpenHistory && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenHistory(toothNumber)}
              className="text-gray-400 hover:text-white"
            >
              <History className="mr-1.5 h-3.5 w-3.5" />
              Ver historial completo
            </Button>
          )}
          <div className="flex-1" />
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="border-gray-600 text-gray-300 hover:bg-gray-800"
          >
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  );
}

ToothDetailModal.displayName = "ToothDetailModal";

export { ToothDetailModal };
