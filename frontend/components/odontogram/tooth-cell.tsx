"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { ZoneData } from "@/lib/hooks/use-odontogram";
import { isAnteriorTooth, ZONE_LABELS } from "@/lib/validations/odontogram";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ToothCellProps {
  /** FDI tooth number (e.g. 11, 16, 55) */
  toothNumber: number;
  /** Current condition data for each zone of this tooth */
  zones: ZoneData[];
  /** Whether this tooth is the currently selected tooth */
  isSelected: boolean;
  /** Currently selected zone within this tooth (null if none) */
  selectedZone: string | null;
  /** Callback when a specific zone is clicked */
  onZoneClick: (toothNumber: number, zone: string) => void;
  /** Callback when the tooth number label is clicked */
  onToothClick: (toothNumber: number) => void;
  /** SVG size in pixels (default: 56) */
  size?: number;
  /** Whether the tooth is in read-only mode */
  readOnly?: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

/**
 * Default zone fill when no condition is present.
 * Using white for light mode visibility with a light gray stroke.
 */
const EMPTY_FILL = "#FFFFFF";
const EMPTY_STROKE = "#CBD5E1"; // slate-300
const CONDITION_STROKE = "#94A3B8"; // slate-400
const SELECTED_STROKE = "#2563EB"; // primary-600
const HOVER_OPACITY = 0.75;

/**
 * SVG polygon points for each zone within a 56x56 viewBox.
 * Crown area occupies the top 40px, root extends below.
 *
 * Layout (cross-shape):
 *          [vestibular]
 *   [mesial] [center] [distal]
 *          [lingual]
 *            [root]
 *
 * For lower jaw teeth, vestibular/lingual swap visually but the
 * zone names remain anatomically correct.
 */
const ZONE_POLYGONS = {
  // Top triangle — vestibular for upper jaw, lingual for lower
  top: "14,0 42,0 35,14 21,14",
  // Bottom triangle — lingual for upper jaw, vestibular for lower
  bottom: "21,26 35,26 42,40 14,40",
  // Left trapezoid — mesial
  left: "0,0 14,0 21,14 21,26 14,40 0,40",
  // Right trapezoid — distal
  right: "42,0 56,0 56,40 42,40 35,26 35,14",
  // Center square — oclusal/incisal
  center: "21,14 35,14 35,26 21,26",
  // Root rectangle below the crown
  root: "18,43 38,43 38,56 18,56",
} as const;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Determines which anatomical zone maps to which SVG position
 * based on whether the tooth is in the upper or lower jaw.
 *
 * Upper jaw (quadrants 1, 2, 5, 6):
 *   top = vestibular, bottom = lingual/palatino
 *
 * Lower jaw (quadrants 3, 4, 7, 8):
 *   top = lingual, bottom = vestibular
 */
function getZonePositionMap(toothNumber: number): Record<string, string> {
  const quadrant = Math.floor(toothNumber / 10);
  const isUpper = [1, 2, 5, 6].includes(quadrant);
  const centerZone = isAnteriorTooth(toothNumber) ? "incisal" : "oclusal";

  if (isUpper) {
    return {
      vestibular: "top",
      lingual: "bottom",
      palatino: "bottom",
      mesial: "left",
      distal: "right",
      [centerZone]: "center",
      root: "root",
    };
  }

  // Lower jaw: vestibular is at the bottom, lingual at top
  return {
    lingual: "top",
    vestibular: "bottom",
    mesial: "left",
    distal: "right",
    [centerZone]: "center",
    root: "root",
  };
}

/**
 * Finds the condition fill color for a given zone.
 */
function getZoneFill(zones: ZoneData[], zoneName: string): string {
  const zoneData = zones.find((z) => z.zone === zoneName);
  if (zoneData?.condition?.condition_color) {
    return zoneData.condition.condition_color;
  }
  return EMPTY_FILL;
}

/**
 * Checks if a zone has an active condition.
 */
function zoneHasCondition(zones: ZoneData[], zoneName: string): boolean {
  const zoneData = zones.find((z) => z.zone === zoneName);
  return zoneData?.condition !== null && zoneData?.condition !== undefined;
}

// ─── ZonePolygon Sub-component ────────────────────────────────────────────────

interface ZonePolygonProps {
  zoneName: string;
  position: string;
  fill: string;
  hasCondition: boolean;
  isZoneSelected: boolean;
  readOnly: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onClick: () => void;
}

function ZonePolygon({
  zoneName,
  position,
  fill,
  hasCondition,
  isZoneSelected,
  readOnly,
  onMouseEnter,
  onMouseLeave,
  onClick,
}: ZonePolygonProps) {
  const points = ZONE_POLYGONS[position as keyof typeof ZONE_POLYGONS];
  if (!points) return null;

  const stroke = isZoneSelected
    ? SELECTED_STROKE
    : hasCondition
      ? CONDITION_STROKE
      : EMPTY_STROKE;

  const strokeWidth = isZoneSelected ? 2 : 1;
  const strokeDasharray = isZoneSelected ? "3,2" : undefined;
  const label = ZONE_LABELS[zoneName] ?? zoneName;

  // Root zone uses a rect for better rendering
  if (position === "root") {
    return (
      <rect
        x={18}
        y={43}
        width={20}
        height={13}
        fill={fill}
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeDasharray={strokeDasharray}
        className={cn(
          "transition-all duration-100",
          !readOnly && "cursor-pointer",
        )}
        style={{ opacity: 1 }}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        onClick={readOnly ? undefined : onClick}
        role={readOnly ? undefined : "button"}
        aria-label={`${label} - Diente ${zoneName}`}
        tabIndex={readOnly ? undefined : 0}
        onKeyDown={
          readOnly
            ? undefined
            : (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onClick();
                }
              }
        }
      />
    );
  }

  return (
    <polygon
      points={points}
      fill={fill}
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeDasharray={strokeDasharray}
      className={cn(
        "transition-all duration-100",
        !readOnly && "cursor-pointer",
      )}
      style={{ opacity: 1 }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onClick={readOnly ? undefined : onClick}
      role={readOnly ? undefined : "button"}
      aria-label={label}
      tabIndex={readOnly ? undefined : 0}
      onKeyDown={
        readOnly
          ? undefined
          : (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick();
              }
            }
      }
    />
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Renders a single tooth as an SVG cross-shape with 5 crown zones + 1 root zone.
 * Each zone is a separate clickable polygon colored by its dental condition.
 *
 * Performance: wrapped in React.memo since the tooth grid renders 32 teeth and
 * most do not change when a single zone is updated.
 */
const ToothCell = React.memo(function ToothCell({
  toothNumber,
  zones,
  isSelected,
  selectedZone,
  onZoneClick,
  onToothClick,
  size = 56,
  readOnly = false,
}: ToothCellProps) {
  const [hoveredZone, setHoveredZone] = React.useState<string | null>(null);

  const quadrant = Math.floor(toothNumber / 10);
  const isUpper = [1, 2, 5, 6].includes(quadrant);
  const isAnterior = isAnteriorTooth(toothNumber);
  const centerZone = isAnterior ? "incisal" : "oclusal";

  // Build the zone-to-position mapping for this tooth
  const zonePositionMap = React.useMemo(
    () => getZonePositionMap(toothNumber),
    [toothNumber],
  );

  // The zones to render (anatomical order, excluding positions that don't apply)
  const zonesToRender = React.useMemo(() => {
    const anatomicalZones = isUpper
      ? ["vestibular", "lingual", "mesial", "distal", centerZone, "root"]
      : ["lingual", "vestibular", "mesial", "distal", centerZone, "root"];

    return anatomicalZones
      .filter((z) => zonePositionMap[z] !== undefined)
      .map((zoneName) => ({
        zoneName,
        position: zonePositionMap[zoneName],
      }));
  }, [isUpper, centerZone, zonePositionMap]);

  // Tooth number label position: above for lower jaw, below for upper jaw
  const labelY = isUpper ? -6 : size + 10;

  return (
    <div
      className={cn(
        "relative flex flex-col items-center",
        isSelected && "z-10",
      )}
    >
      {/* Tooth number label — above for lower quadrants, below for upper */}
      {!isUpper && (
        <button
          type="button"
          onClick={() => onToothClick(toothNumber)}
          className={cn(
            "mb-1 text-[10px] font-semibold tabular-nums leading-none",
            "transition-colors duration-100",
            isSelected
              ? "text-primary-600"
              : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
            !readOnly && "cursor-pointer",
          )}
          aria-label={`Seleccionar diente ${toothNumber}`}
          disabled={readOnly}
        >
          {toothNumber}
        </button>
      )}

      {/* SVG tooth diagram */}
      <div
        className={cn(
          "relative rounded-sm transition-shadow duration-150",
          isSelected && "ring-2 ring-primary-600 ring-offset-1 ring-offset-[hsl(var(--background))]",
        )}
      >
        <svg
          width={size}
          height={size}
          viewBox="0 0 56 56"
          xmlns="http://www.w3.org/2000/svg"
          aria-label={`Diente ${toothNumber} - ${isAnterior ? "Anterior" : "Posterior"}`}
          role="img"
        >
          {/* Render zones in back-to-front order: outer zones first, center last */}
          {zonesToRender.map(({ zoneName, position }) => {
            const fill = getZoneFill(zones, zoneName);
            const hasCondition = zoneHasCondition(zones, zoneName);
            const isZoneSelected =
              isSelected && selectedZone === zoneName;
            const isHovered = hoveredZone === zoneName;

            // Apply a semi-transparent overlay on hover
            const displayFill = isHovered && !readOnly
              ? fill === EMPTY_FILL
                ? "#EFF6FF" // light blue tint on hover for empty zones
                : fill
              : fill;

            return (
              <g
                key={zoneName}
                style={{ opacity: isHovered && !readOnly ? HOVER_OPACITY : 1 }}
              >
                <ZonePolygon
                  zoneName={zoneName}
                  position={position}
                  fill={displayFill}
                  hasCondition={hasCondition}
                  isZoneSelected={isZoneSelected}
                  readOnly={readOnly}
                  onMouseEnter={() => setHoveredZone(zoneName)}
                  onMouseLeave={() => setHoveredZone(null)}
                  onClick={() => onZoneClick(toothNumber, zoneName)}
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Tooth number label — below for upper quadrants */}
      {isUpper && (
        <button
          type="button"
          onClick={() => onToothClick(toothNumber)}
          className={cn(
            "mt-1 text-[10px] font-semibold tabular-nums leading-none",
            "transition-colors duration-100",
            isSelected
              ? "text-primary-600"
              : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
            !readOnly && "cursor-pointer",
          )}
          aria-label={`Seleccionar diente ${toothNumber}`}
          disabled={readOnly}
        >
          {toothNumber}
        </button>
      )}
    </div>
  );
});

ToothCell.displayName = "ToothCell";

export { ToothCell };
