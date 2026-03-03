"use client";

import * as React from "react";
import { X, History, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { ToothData, ZoneData, CatalogCondition } from "@/lib/hooks/use-odontogram";
import { isAnteriorTooth, ZONE_LABELS } from "@/lib/validations/odontogram";
import { TOOTH_NAMES_ES, getToothRootCount } from "@/lib/odontogram/tooth-paths";
import {
  EMPTY_FILL_DARK,
  EMPTY_STROKE_DARK,
  CONDITION_STROKE,
  SELECTED_STROKE,
  getZoneFill,
  zoneHasCondition,
} from "@/lib/odontogram/zone-helpers";
import { ZoneChips } from "./zone-chips";

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

// ─── Anatomic Zone Diagram (dark theme, large, with roots) ──────────────────

/**
 * Crown polygon points within a 140×185 viewBox.
 * Crown occupies y=0..100, cervical line at y=105, roots y=110..178.
 *
 * Layout (cross-shape):
 *        [  top zone  ]
 * [left] [ center ] [right]
 *        [bottom zone ]
 *     ---- cervical ----
 *        [  roots   ]
 */
const MODAL_CROWN_POLYGONS = {
  top: "30,0 110,0 92,28 48,28",
  left: "0,0 30,0 48,28 48,72 30,100 0,100",
  center: "48,28 92,28 92,72 48,72",
  right: "110,0 140,0 140,100 110,100 92,72 92,28",
  bottom: "48,72 92,72 110,100 30,100",
} as const;

type ModalZonePosition = keyof typeof MODAL_CROWN_POLYGONS | "root";

/** Text label center positions for each zone */
const MODAL_LABEL_POS: Record<ModalZonePosition, { x: number; y: number }> = {
  top: { x: 70, y: 14 },
  left: { x: 20, y: 50 },
  center: { x: 70, y: 50 },
  right: { x: 120, y: 50 },
  bottom: { x: 70, y: 86 },
  root: { x: 70, y: 148 },
};

/** Abbreviated zone labels for inside the diagram */
const SHORT_ZONE_LABELS: Record<string, string> = {
  vestibular: "Vest.",
  lingual: "Ling.",
  mesial: "Mes.",
  distal: "Dist.",
  oclusal: "Ocl.",
  incisal: "Inc.",
  root: "Raíz",
};

/** Build SVG path strings for anatomic root shapes by root count */
function buildModalRootPaths(rootCount: number): string[] {
  if (rootCount <= 1) {
    // Single tapered root, centered
    return [
      "M52,110 L88,110 Q86,145 76,178 L64,178 Q54,145 52,110 Z",
    ];
  }
  if (rootCount === 2) {
    // Two roots side by side
    return [
      "M28,110 L60,110 Q58,140 50,174 L38,174 Q30,140 28,110 Z",
      "M80,110 L112,110 Q110,140 102,174 L90,174 Q82,140 80,110 Z",
    ];
  }
  // Three roots (molars)
  return [
    "M12,110 L40,110 Q38,135 33,170 L21,170 Q16,135 12,110 Z",
    "M50,110 L90,110 Q88,135 79,166 L61,166 Q52,135 50,110 Z",
    "M100,110 L128,110 Q126,135 121,170 L109,170 Q104,135 100,110 Z",
  ];
}

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
  const rootCount = getToothRootCount(toothNumber);

  // Map anatomical zone names → SVG positions
  const topZone = isUpper ? "vestibular" : "lingual";
  const bottomZone = isUpper ? "lingual" : "vestibular";

  const zoneConfig: { name: string; position: ModalZonePosition }[] = [
    { name: topZone, position: "top" },
    { name: "mesial", position: "left" },
    { name: centerZone, position: "center" },
    { name: "distal", position: "right" },
    { name: bottomZone, position: "bottom" },
    { name: "root", position: "root" },
  ];

  const rootPaths = React.useMemo(
    () => buildModalRootPaths(rootCount),
    [rootCount],
  );

  /** Compute visual + interaction props for a zone */
  function getZoneProps(zoneName: string) {
    const fill = getZoneFill(zones, zoneName, true);
    const hasCondition = zoneHasCondition(zones, zoneName);
    const isZoneSelected = selectedZone === zoneName;
    const isHovered = hoveredZone === zoneName;

    const stroke = isZoneSelected
      ? SELECTED_STROKE
      : hasCondition
        ? CONDITION_STROKE
        : EMPTY_STROKE_DARK;
    const strokeWidth = isZoneSelected ? 2.5 : 1;
    const strokeDasharray = isZoneSelected ? "5,3" : undefined;

    const displayFill =
      isHovered && !readOnly
        ? fill === EMPTY_FILL_DARK
          ? "#4B5563"
          : fill
        : fill;

    const opacity = isHovered && !readOnly ? 0.85 : 1;

    return {
      fill: displayFill,
      stroke,
      strokeWidth,
      strokeDasharray,
      opacity,
      className: cn(
        "transition-all duration-100",
        !readOnly && "cursor-pointer",
      ),
      onMouseEnter: () => setHoveredZone(zoneName),
      onMouseLeave: () => setHoveredZone(null),
      onClick: () => !readOnly && onZoneClick(zoneName),
      role: readOnly ? undefined : ("button" as const),
      "aria-label": ZONE_LABELS[zoneName] ?? zoneName,
      tabIndex: readOnly ? undefined : 0,
      onKeyDown: readOnly
        ? undefined
        : (e: React.KeyboardEvent) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onZoneClick(zoneName);
            }
          },
    };
  }

  return (
    <svg
      width={210}
      height={278}
      viewBox="0 0 140 185"
      xmlns="http://www.w3.org/2000/svg"
      className="drop-shadow-lg"
      aria-label={`Diagrama de zonas — Diente ${toothNumber}`}
      role="img"
    >
      {zoneConfig.map(({ name, position }) => {
        const props = getZoneProps(name);
        const labelPos = MODAL_LABEL_POS[position];
        const shortLabel = SHORT_ZONE_LABELS[name] ?? name;
        const isSelected = selectedZone === name;

        if (position === "root") {
          return (
            <g key={name}>
              {/* Anatomic root shapes (1–3 based on tooth type) */}
              {rootPaths.map((d, i) => (
                <path
                  key={i}
                  d={d}
                  fill={props.fill}
                  stroke={props.stroke}
                  strokeWidth={props.strokeWidth}
                  strokeDasharray={props.strokeDasharray}
                  opacity={props.opacity}
                  pointerEvents="none"
                />
              ))}
              {/* Invisible hit area covering entire root region */}
              <rect
                x={8}
                y={108}
                width={124}
                height={76}
                fill="transparent"
                className={props.className}
                onMouseEnter={props.onMouseEnter}
                onMouseLeave={props.onMouseLeave}
                onClick={props.onClick}
                role={props.role}
                aria-label={props["aria-label"]}
                tabIndex={props.tabIndex}
                onKeyDown={props.onKeyDown}
              />
              {/* Root label */}
              <text
                x={labelPos.x}
                y={labelPos.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={isSelected ? "#93C5FD" : "#9CA3AF"}
                fontSize={9}
                fontWeight={isSelected ? 600 : 400}
                className="pointer-events-none select-none"
              >
                {shortLabel}
              </text>
            </g>
          );
        }

        return (
          <g key={name}>
            <polygon
              points={MODAL_CROWN_POLYGONS[position]}
              {...props}
            />
            {/* Zone label */}
            <text
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill={isSelected ? "#93C5FD" : "#9CA3AF"}
              fontSize={position === "center" ? 10 : 9}
              fontWeight={isSelected ? 600 : 400}
              className="pointer-events-none select-none"
            >
              {shortLabel}
            </text>
          </g>
        );
      })}

      {/* Cervical line (dashed) separating crown from roots */}
      <line
        x1={10}
        y1={105}
        x2={130}
        y2={105}
        stroke="#6B7280"
        strokeWidth={1}
        strokeDasharray="4,3"
        className="pointer-events-none"
      />
    </svg>
  );
}

// ─── Simple Condition Grid (matches Notion design) ───────────────────────────

interface ConditionGridProps {
  conditions: CatalogCondition[];
  selectedCondition: string | null;
  selectedZone: string | null;
  onConditionSelect: (code: string) => void;
  disabled: boolean;
}

function ConditionGrid({
  conditions,
  selectedCondition,
  selectedZone,
  onConditionSelect,
  disabled,
}: ConditionGridProps) {
  // Filter conditions by zone validity (same logic as grid view's condition-panel)
  const allConditions = Array.isArray(conditions) ? conditions : [];
  const filteredConditions = selectedZone
    ? allConditions.filter(
        (c) => c.zones.length === 0 || c.zones.includes(selectedZone),
      )
    : allConditions;

  return (
    <div
      className={cn(
        "rounded-lg border border-gray-700 bg-gray-800/50 p-4",
        disabled && "opacity-50 pointer-events-none",
      )}
    >
      <h3 className="text-sm font-semibold text-white mb-1">
        Condiciones dentales
      </h3>
      <p className="text-xs text-gray-400 mb-4">
        {selectedZone
          ? `${filteredConditions.length} condiciones disponibles para esta zona.`
          : "Selecciona una zona del diente para aplicar una condicion."}
      </p>

      {/* 2-column condition grid with colored dots */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-3">
        {filteredConditions.map((c) => {
          const isActive = selectedCondition === c.code;
          return (
            <button
              key={c.code}
              type="button"
              onClick={() => onConditionSelect(c.code)}
              disabled={disabled}
              className={cn(
                "flex items-center gap-2.5 text-left text-sm rounded-md px-1.5 py-1 -mx-1.5",
                "transition-colors duration-100",
                isActive
                  ? "bg-gray-700/60 text-white"
                  : "text-gray-300 hover:text-white hover:bg-gray-700/30",
              )}
            >
              <span
                className={cn(
                  "shrink-0 h-3 w-3 rounded-full",
                  isActive && "ring-2 ring-offset-1 ring-offset-gray-800 ring-white/40",
                )}
                style={{ backgroundColor: c.color_hex }}
              />
              <span className="truncate">{c.name_es}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Modal Component ──────────────────────────────────────────────────────────

/**
 * Full-screen modal overlay for tooth detail in anatomic view.
 * Shows a 6-zone interactive diagram on the left and a simple 2-column
 * condition grid on the right, matching the Notion dark-theme design.
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
  }, []);

  const handleConditionSelect = React.useCallback(
    (code: string) => {
      setSelectedCondition(selectedCondition === code ? null : code);
    },
    [selectedCondition],
  );

  const handleApply = React.useCallback(() => {
    if (!selectedZone || !selectedCondition) return;
    onApply({
      tooth_number: toothNumber,
      zone: selectedZone,
      condition_code: selectedCondition,
      severity: null,
      notes: null,
      source: "manual",
    });
    // Reset condition after apply
    setSelectedCondition(null);
  }, [toothNumber, selectedZone, selectedCondition, onApply]);

  const canApply = selectedZone !== null && selectedCondition !== null && !isSaving;

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
          "relative w-full max-w-[680px] max-h-[90vh] overflow-y-auto",
          "rounded-xl border border-gray-700 bg-gray-900 p-6 shadow-2xl",
          "transition-transform duration-200 ease-out",
          isVisible ? "scale-100" : "scale-95",
        )}
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">
              Diente {toothNumber}
            </h2>
            <p className="text-sm text-gray-400 mt-0.5">{toothName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            aria-label="Cerrar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ── Content Grid ───────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-6">
          {/* Left column: Zone diagram + zone info + chips */}
          <div className="flex flex-col items-center gap-3 shrink-0 sm:w-[240px]">
            <ZoneDiagram
              toothNumber={toothNumber}
              zones={toothData.zones}
              selectedZone={selectedZone}
              onZoneClick={handleZoneClick}
              readOnly={readOnly}
            />

            {/* Zone selection text */}
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

            {/* Zone chips — current findings */}
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

          {/* Right column: Condition grid + Apply button */}
          {!readOnly && (
            <div className="flex-1 min-w-0 flex flex-col gap-4">
              <ConditionGrid
                conditions={conditions}
                selectedCondition={selectedCondition}
                selectedZone={selectedZone}
                onConditionSelect={handleConditionSelect}
                disabled={selectedZone === null}
              />

              {/* Apply button — prominent blue, full width */}
              <Button
                onClick={handleApply}
                disabled={!canApply}
                className={cn(
                  "w-full h-10",
                  canApply
                    ? "bg-blue-600 hover:bg-blue-700 text-white"
                    : "bg-gray-700 text-gray-400 cursor-not-allowed",
                )}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Aplicando...
                  </>
                ) : (
                  "Aplicar"
                )}
              </Button>
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

        {/* ── Footer ─────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-700">
          {onOpenHistory ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenHistory(toothNumber)}
              className="text-gray-400 hover:text-white"
            >
              <History className="mr-1.5 h-3.5 w-3.5" />
              Ver historial completo
            </Button>
          ) : (
            <div />
          )}
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
