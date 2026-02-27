"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { ZoneData } from "@/lib/hooks/use-odontogram";
import { isAnteriorTooth, ZONE_LABELS } from "@/lib/validations/odontogram";
import {
  ZONE_POLYGONS,
  EMPTY_FILL,
  EMPTY_STROKE,
  CONDITION_STROKE,
  SELECTED_STROKE,
  getZonePositionMap,
  getZoneFill,
  zoneHasCondition,
  type ZonePosition,
} from "@/lib/odontogram/zone-helpers";

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

const HOVER_OPACITY = 0.75;

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
  const points = ZONE_POLYGONS[position as ZonePosition];
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
