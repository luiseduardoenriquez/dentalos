"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { ToothData } from "@/lib/hooks/use-odontogram";
import type { DentitionType } from "@/lib/validations/odontogram";
import { ADULT_TEETH } from "@/lib/validations/odontogram";
import {
  TOOTH_ARCH_POSITIONS,
  TOOTH_NAMES_ES,
  ARCH_GEOMETRY,
  type ToothArchPosition,
  type ToothType,
} from "@/lib/odontogram/tooth-paths";
import { getWorstZoneColor } from "@/lib/odontogram/zone-helpers";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ToothArchSVGProps {
  /** All tooth data from the odontogram API */
  teeth: ToothData[];
  /** Current dentition type */
  dentitionType: DentitionType;
  /** Currently selected tooth (null if none) */
  selectedTooth: number | null;
  /** Callback when a tooth is clicked */
  onToothClick: (toothNumber: number) => void;
  /** Read-only mode (no interactions) */
  readOnly?: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const HEALTHY_FILL = "#374151"; // gray-700
const TOOTH_STROKE = "#4B5563"; // gray-600
const SELECTED_GLOW_COLOR = "#3B82F6"; // blue-500
const HOVER_GLOW_COLOR = "#0EA5E9"; // sky-500
const BADGE_BG_COLOR = "#0EA5E9"; // sky-500 for FDI badge on hover
const CONDITION_BADGE_COLOR = "#EF4444"; // red-500
const BG_COLOR = "#030712"; // gray-950
const GUIDE_STROKE = "#1F2937"; // gray-800
const LABEL_COLOR = "#4B5563"; // gray-600
const CERVICAL_LINE_COLOR = "#6B7280"; // gray-500
const MIN_HIT_AREA = 44; // px — tablet touch target minimum

// ─── Anatomic SVG tooth shape paths ─────────────────────────────────────────
//
// Each function returns an SVG <path> d attribute string for a tooth shape
// centered at (0, 0). The crown is always drawn in the center, and roots
// extend outward. For upper teeth, roots point UP (negative y). For lower
// teeth, roots point DOWN (positive y).
//
// The coordinate system: (0,0) is the center of the crown.
// Crown height is roughly the upper half of the total height, roots the other.

/**
 * Build anatomic SVG path for an incisor tooth.
 * Narrow crown with slight taper, 1 thin root.
 *
 * @param w - tooth width
 * @param h - tooth height
 * @param arch - "upper" or "lower"
 * @returns object with crownPath, rootPaths[], and cervicalY
 */
function buildIncisorPaths(
  w: number,
  h: number,
  arch: "upper" | "lower",
): { crownPath: string; rootPaths: string[]; cervicalY: number } {
  const crownH = h * 0.55;
  const rootH = h * 0.45;

  if (arch === "upper") {
    // Crown at bottom (toward mouth), roots at top (toward palate)
    const crownTop = 0;
    const crownBot = crownH;
    const cervicalY = crownTop;
    const rootTop = -rootH;

    // Crown: slightly tapered rectangle with rounded bottom
    const crownPath = [
      `M ${-w * 0.4},${crownTop}`,
      `L ${-w * 0.45},${crownBot * 0.3}`,
      `Q ${-w * 0.48},${crownBot} ${-w * 0.15},${crownBot}`,
      `L ${w * 0.15},${crownBot}`,
      `Q ${w * 0.48},${crownBot} ${w * 0.45},${crownBot * 0.3}`,
      `L ${w * 0.4},${crownTop}`,
      `Z`,
    ].join(" ");

    // Single thin root pointing up
    const rootPath = [
      `M ${-w * 0.2},${cervicalY}`,
      `Q ${-w * 0.18},${rootTop * 0.5} ${-w * 0.05},${rootTop}`,
      `Q ${w * 0.18},${rootTop * 0.5} ${w * 0.2},${cervicalY}`,
    ].join(" ");

    return { crownPath, rootPaths: [rootPath], cervicalY };
  }

  // Lower arch: crown at top, roots at bottom
  const crownTop = -crownH;
  const crownBot = 0;
  const cervicalY = crownBot;
  const rootBot = rootH;

  const crownPath = [
    `M ${-w * 0.4},${crownBot}`,
    `L ${-w * 0.45},${crownTop * 0.3 + crownBot * 0.7}`,
    `Q ${-w * 0.48},${crownTop} ${-w * 0.15},${crownTop}`,
    `L ${w * 0.15},${crownTop}`,
    `Q ${w * 0.48},${crownTop} ${w * 0.45},${crownTop * 0.3 + crownBot * 0.7}`,
    `L ${w * 0.4},${crownBot}`,
    `Z`,
  ].join(" ");

  const rootPath = [
    `M ${-w * 0.2},${cervicalY}`,
    `Q ${-w * 0.18},${rootBot * 0.5} ${-w * 0.05},${rootBot}`,
    `Q ${w * 0.18},${rootBot * 0.5} ${w * 0.2},${cervicalY}`,
  ].join(" ");

  return { crownPath, rootPaths: [rootPath], cervicalY };
}

/**
 * Build anatomic SVG path for a canine tooth.
 * Pointed crown (wider at top, tapers to a cusp), 1 long root.
 */
function buildCaninePaths(
  w: number,
  h: number,
  arch: "upper" | "lower",
): { crownPath: string; rootPaths: string[]; cervicalY: number } {
  const crownH = h * 0.5;
  const rootH = h * 0.5;

  if (arch === "upper") {
    const crownTop = 0;
    const crownBot = crownH;
    const cervicalY = crownTop;
    const rootTop = -rootH;

    // Crown: pointed shape tapering to a cusp at the incisal edge
    const crownPath = [
      `M ${-w * 0.42},${crownTop}`,
      `L ${-w * 0.48},${crownBot * 0.4}`,
      `L ${-w * 0.3},${crownBot * 0.85}`,
      `L 0,${crownBot}`,
      `L ${w * 0.3},${crownBot * 0.85}`,
      `L ${w * 0.48},${crownBot * 0.4}`,
      `L ${w * 0.42},${crownTop}`,
      `Z`,
    ].join(" ");

    // Long single root
    const rootPath = [
      `M ${-w * 0.22},${cervicalY}`,
      `Q ${-w * 0.2},${rootTop * 0.4} ${-w * 0.08},${rootTop * 0.85}`,
      `L 0,${rootTop}`,
      `L ${w * 0.08},${rootTop * 0.85}`,
      `Q ${w * 0.2},${rootTop * 0.4} ${w * 0.22},${cervicalY}`,
    ].join(" ");

    return { crownPath, rootPaths: [rootPath], cervicalY };
  }

  // Lower
  const crownTop = -crownH;
  const crownBot = 0;
  const cervicalY = crownBot;
  const rootBot = rootH;

  const crownPath = [
    `M ${-w * 0.42},${crownBot}`,
    `L ${-w * 0.48},${crownBot + (crownTop - crownBot) * 0.4}`,
    `L ${-w * 0.3},${crownBot + (crownTop - crownBot) * 0.85}`,
    `L 0,${crownTop}`,
    `L ${w * 0.3},${crownBot + (crownTop - crownBot) * 0.85}`,
    `L ${w * 0.48},${crownBot + (crownTop - crownBot) * 0.4}`,
    `L ${w * 0.42},${crownBot}`,
    `Z`,
  ].join(" ");

  const rootPath = [
    `M ${-w * 0.22},${cervicalY}`,
    `Q ${-w * 0.2},${rootBot * 0.4} ${-w * 0.08},${rootBot * 0.85}`,
    `L 0,${rootBot}`,
    `L ${w * 0.08},${rootBot * 0.85}`,
    `Q ${w * 0.2},${rootBot * 0.4} ${w * 0.22},${cervicalY}`,
  ].join(" ");

  return { crownPath, rootPaths: [rootPath], cervicalY };
}

/**
 * Build anatomic SVG path for a premolar tooth.
 * Medium crown with 2 cusps at the occlusal surface, 2 roots.
 */
function buildPremolarPaths(
  w: number,
  h: number,
  arch: "upper" | "lower",
): { crownPath: string; rootPaths: string[]; cervicalY: number } {
  const crownH = h * 0.55;
  const rootH = h * 0.45;

  if (arch === "upper") {
    const crownTop = 0;
    const crownBot = crownH;
    const cervicalY = crownTop;
    const rootTop = -rootH;

    // Crown with 2 cusps at the bottom (occlusal)
    const crownPath = [
      `M ${-w * 0.45},${crownTop}`,
      `L ${-w * 0.48},${crownBot * 0.5}`,
      `L ${-w * 0.4},${crownBot * 0.85}`,
      `L ${-w * 0.15},${crownBot * 0.75}`,
      `L 0,${crownBot}`,
      `L ${w * 0.15},${crownBot * 0.75}`,
      `L ${w * 0.4},${crownBot * 0.85}`,
      `L ${w * 0.48},${crownBot * 0.5}`,
      `L ${w * 0.45},${crownTop}`,
      `Z`,
    ].join(" ");

    // 2 roots — buccal and palatal
    const rootLeft = [
      `M ${-w * 0.3},${cervicalY}`,
      `Q ${-w * 0.32},${rootTop * 0.4} ${-w * 0.2},${rootTop * 0.9}`,
      `L ${-w * 0.12},${rootTop}`,
      `Q ${-w * 0.05},${rootTop * 0.5} ${-w * 0.02},${cervicalY}`,
    ].join(" ");

    const rootRight = [
      `M ${w * 0.02},${cervicalY}`,
      `Q ${w * 0.05},${rootTop * 0.5} ${w * 0.12},${rootTop}`,
      `L ${w * 0.2},${rootTop * 0.9}`,
      `Q ${w * 0.32},${rootTop * 0.4} ${w * 0.3},${cervicalY}`,
    ].join(" ");

    return { crownPath, rootPaths: [rootLeft, rootRight], cervicalY };
  }

  // Lower
  const crownTop = -crownH;
  const crownBot = 0;
  const cervicalY = crownBot;
  const rootBot = rootH;

  const crownPath = [
    `M ${-w * 0.45},${crownBot}`,
    `L ${-w * 0.48},${crownBot + (crownTop - crownBot) * 0.5}`,
    `L ${-w * 0.4},${crownBot + (crownTop - crownBot) * 0.85}`,
    `L ${-w * 0.15},${crownBot + (crownTop - crownBot) * 0.75}`,
    `L 0,${crownTop}`,
    `L ${w * 0.15},${crownBot + (crownTop - crownBot) * 0.75}`,
    `L ${w * 0.4},${crownBot + (crownTop - crownBot) * 0.85}`,
    `L ${w * 0.48},${crownBot + (crownTop - crownBot) * 0.5}`,
    `L ${w * 0.45},${crownBot}`,
    `Z`,
  ].join(" ");

  const rootLeft = [
    `M ${-w * 0.3},${cervicalY}`,
    `Q ${-w * 0.32},${rootBot * 0.4} ${-w * 0.2},${rootBot * 0.9}`,
    `L ${-w * 0.12},${rootBot}`,
    `Q ${-w * 0.05},${rootBot * 0.5} ${-w * 0.02},${cervicalY}`,
  ].join(" ");

  const rootRight = [
    `M ${w * 0.02},${cervicalY}`,
    `Q ${w * 0.05},${rootBot * 0.5} ${w * 0.12},${rootBot}`,
    `L ${w * 0.2},${rootBot * 0.9}`,
    `Q ${w * 0.32},${rootBot * 0.4} ${w * 0.3},${cervicalY}`,
  ].join(" ");

  return { crownPath, rootPaths: [rootLeft, rootRight], cervicalY };
}

/**
 * Build anatomic SVG path for a molar tooth.
 * Wide crown with 3 rounded cusps at the occlusal surface, 3 roots
 * (2 buccal + 1 palatal).
 */
function buildMolarPaths(
  w: number,
  h: number,
  arch: "upper" | "lower",
): { crownPath: string; rootPaths: string[]; cervicalY: number } {
  const crownH = h * 0.52;
  const rootH = h * 0.48;

  if (arch === "upper") {
    const crownTop = 0;
    const crownBot = crownH;
    const cervicalY = crownTop;
    const rootTop = -rootH;

    // Crown with 3 rounded bumps (cusps) at the bottom
    const crownPath = [
      `M ${-w * 0.46},${crownTop}`,
      `L ${-w * 0.5},${crownBot * 0.5}`,
      `Q ${-w * 0.48},${crownBot * 0.9} ${-w * 0.3},${crownBot * 0.82}`,
      `Q ${-w * 0.18},${crownBot * 0.72} ${-w * 0.08},${crownBot * 0.9}`,
      `Q 0,${crownBot} ${w * 0.08},${crownBot * 0.9}`,
      `Q ${w * 0.18},${crownBot * 0.72} ${w * 0.3},${crownBot * 0.82}`,
      `Q ${w * 0.48},${crownBot * 0.9} ${w * 0.5},${crownBot * 0.5}`,
      `L ${w * 0.46},${crownTop}`,
      `Z`,
    ].join(" ");

    // 3 roots: left buccal, center (palatal), right buccal
    const rootLeft = [
      `M ${-w * 0.35},${cervicalY}`,
      `Q ${-w * 0.38},${rootTop * 0.3} ${-w * 0.3},${rootTop * 0.8}`,
      `L ${-w * 0.22},${rootTop}`,
      `Q ${-w * 0.15},${rootTop * 0.5} ${-w * 0.12},${cervicalY}`,
    ].join(" ");

    const rootCenter = [
      `M ${-w * 0.08},${cervicalY}`,
      `Q ${-w * 0.05},${rootTop * 0.35} 0,${rootTop * 0.85}`,
      `L ${w * 0.02},${rootTop * 0.82}`,
      `Q ${w * 0.05},${rootTop * 0.35} ${w * 0.08},${cervicalY}`,
    ].join(" ");

    const rootRight = [
      `M ${w * 0.12},${cervicalY}`,
      `Q ${w * 0.15},${rootTop * 0.5} ${w * 0.22},${rootTop}`,
      `L ${w * 0.3},${rootTop * 0.8}`,
      `Q ${w * 0.38},${rootTop * 0.3} ${w * 0.35},${cervicalY}`,
    ].join(" ");

    return {
      crownPath,
      rootPaths: [rootLeft, rootCenter, rootRight],
      cervicalY,
    };
  }

  // Lower
  const crownTop = -crownH;
  const crownBot = 0;
  const cervicalY = crownBot;
  const rootBot = rootH;

  const crownPath = [
    `M ${-w * 0.46},${crownBot}`,
    `L ${-w * 0.5},${crownBot + (crownTop - crownBot) * 0.5}`,
    `Q ${-w * 0.48},${crownBot + (crownTop - crownBot) * 0.9} ${-w * 0.3},${crownBot + (crownTop - crownBot) * 0.82}`,
    `Q ${-w * 0.18},${crownBot + (crownTop - crownBot) * 0.72} ${-w * 0.08},${crownBot + (crownTop - crownBot) * 0.9}`,
    `Q 0,${crownTop} ${w * 0.08},${crownBot + (crownTop - crownBot) * 0.9}`,
    `Q ${w * 0.18},${crownBot + (crownTop - crownBot) * 0.72} ${w * 0.3},${crownBot + (crownTop - crownBot) * 0.82}`,
    `Q ${w * 0.48},${crownBot + (crownTop - crownBot) * 0.9} ${w * 0.5},${crownBot + (crownTop - crownBot) * 0.5}`,
    `L ${w * 0.46},${crownBot}`,
    `Z`,
  ].join(" ");

  // Lower molars typically have 2 roots, but we render 3 for anatomic accuracy
  const rootLeft = [
    `M ${-w * 0.35},${cervicalY}`,
    `Q ${-w * 0.38},${rootBot * 0.3} ${-w * 0.3},${rootBot * 0.8}`,
    `L ${-w * 0.22},${rootBot}`,
    `Q ${-w * 0.15},${rootBot * 0.5} ${-w * 0.12},${cervicalY}`,
  ].join(" ");

  const rootCenter = [
    `M ${-w * 0.08},${cervicalY}`,
    `Q ${-w * 0.05},${rootBot * 0.35} 0,${rootBot * 0.85}`,
    `L ${w * 0.02},${rootBot * 0.82}`,
    `Q ${w * 0.05},${rootBot * 0.35} ${w * 0.08},${cervicalY}`,
  ].join(" ");

  const rootRight = [
    `M ${w * 0.12},${cervicalY}`,
    `Q ${w * 0.15},${rootBot * 0.5} ${w * 0.22},${rootBot}`,
    `L ${w * 0.3},${rootBot * 0.8}`,
    `Q ${w * 0.38},${rootBot * 0.3} ${w * 0.35},${cervicalY}`,
  ].join(" ");

  return {
    crownPath,
    rootPaths: [rootLeft, rootCenter, rootRight],
    cervicalY,
  };
}

/**
 * Build the anatomic SVG paths for a tooth based on its type.
 */
function buildToothShapePaths(
  toothType: ToothType,
  w: number,
  h: number,
  arch: "upper" | "lower",
): { crownPath: string; rootPaths: string[]; cervicalY: number } {
  switch (toothType) {
    case "incisor":
      return buildIncisorPaths(w, h, arch);
    case "canine":
      return buildCaninePaths(w, h, arch);
    case "premolar":
      return buildPremolarPaths(w, h, arch);
    case "molar":
      return buildMolarPaths(w, h, arch);
  }
}

// ─── SingleTooth (memoized) ──────────────────────────────────────────────────

interface SingleToothProps {
  position: ToothArchPosition;
  toothData: ToothData | undefined;
  isSelected: boolean;
  readOnly: boolean;
  onToothClick: (toothNumber: number) => void;
}

const SingleTooth = React.memo(function SingleTooth({
  position,
  toothData,
  isSelected,
  readOnly,
  onToothClick,
}: SingleToothProps) {
  const [isHovered, setIsHovered] = React.useState(false);
  const { toothNumber, cx, cy, angle, width, height, toothType, arch } =
    position;

  // Determine tooth color from worst zone condition
  const conditionColor = toothData
    ? getWorstZoneColor(toothData.zones)
    : null;
  const fill = conditionColor ?? HEALTHY_FILL;

  // Count conditions for badge
  const conditionCount = toothData
    ? toothData.zones.filter((z) => z.condition).length
    : 0;

  // Build anatomic SVG paths
  const { crownPath, rootPaths, cervicalY } = React.useMemo(
    () => buildToothShapePaths(toothType, width, height, arch),
    [toothType, width, height, arch],
  );

  // Ensure hit area meets minimum touch target
  const hitWidth = Math.max(width + 12, MIN_HIT_AREA);
  const hitHeight = Math.max(height + 12, MIN_HIT_AREA);

  const toothName = TOOTH_NAMES_ES[toothNumber] ?? `Diente ${toothNumber}`;

  // Determine visual scale based on state
  const scale = isHovered && !readOnly ? 1.25 : isSelected ? 1.08 : 1;

  // Tooltip position: above the tooth for upper arch, below for lower
  const tooltipY = arch === "upper" ? -height * 0.6 - 28 : height * 0.6 + 14;

  // FDI label position: below for upper, above for lower
  const fdiLabelY = arch === "upper" ? height * 0.6 + 11 : -height * 0.6 - 5;

  return (
    <g
      transform={`translate(${cx}, ${cy}) rotate(${angle})`}
      className="tooth-element"
      role={readOnly ? "img" : "button"}
      aria-label={`${toothName} — ${conditionColor ? "Con hallazgos" : "Sano"}`}
      tabIndex={readOnly ? undefined : 0}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => !readOnly && onToothClick(toothNumber)}
      onKeyDown={
        readOnly
          ? undefined
          : (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onToothClick(toothNumber);
              }
            }
      }
      style={{ cursor: readOnly ? "default" : "pointer" }}
    >
      {/* Invisible expanded hit area for touch targets */}
      <rect
        x={-hitWidth / 2}
        y={-hitHeight / 2}
        width={hitWidth}
        height={hitHeight}
        fill="transparent"
        aria-hidden="true"
      />

      {/* Tooth group with scale transform for hover/selection */}
      <g
        className={cn(
          "origin-center",
          "transition-transform duration-200",
          "[transition-timing-function:cubic-bezier(0.34,1.56,0.64,1)]",
          "motion-reduce:!transition-none motion-reduce:!transform-none",
        )}
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "0 0",
        }}
      >
        {/* Hover glow ring */}
        {isHovered && !readOnly && (
          <circle
            cx={0}
            cy={0}
            r={Math.max(width, height) * 0.55}
            fill="none"
            stroke={HOVER_GLOW_COLOR}
            strokeWidth={1.5}
            opacity={0.6}
            className={cn(
              "motion-reduce:opacity-80",
            )}
            style={{
              filter: `drop-shadow(0 0 4px ${HOVER_GLOW_COLOR})`,
            }}
          />
        )}

        {/* Selection glow */}
        {isSelected && (
          <circle
            cx={0}
            cy={0}
            r={Math.max(width, height) * 0.55}
            fill="none"
            stroke={SELECTED_GLOW_COLOR}
            strokeWidth={2}
            className="animate-pulse"
            style={{
              filter: `drop-shadow(0 0 8px ${SELECTED_GLOW_COLOR})`,
            }}
          />
        )}

        {/* Root paths — drawn behind the crown */}
        {rootPaths.map((rp, idx) => (
          <path
            key={`root-${idx}`}
            d={rp}
            fill={fill}
            stroke={isSelected ? SELECTED_GLOW_COLOR : TOOTH_STROKE}
            strokeWidth={isSelected ? 1 : 0.6}
            opacity={0.85}
          />
        ))}

        {/* Cervical line (dashed) between crown and roots */}
        <line
          x1={-width * 0.45}
          y1={cervicalY}
          x2={width * 0.45}
          y2={cervicalY}
          stroke={CERVICAL_LINE_COLOR}
          strokeWidth={0.5}
          strokeDasharray="1.5,1.5"
          opacity={0.7}
        />

        {/* Crown path — the main visible tooth shape */}
        <path
          d={crownPath}
          fill={fill}
          stroke={isSelected ? SELECTED_GLOW_COLOR : TOOTH_STROKE}
          strokeWidth={isSelected ? 1.2 : 0.75}
          strokeLinejoin="round"
        />

        {/* Condition count badge (red circle) if multiple zones have conditions */}
        {conditionCount > 1 && (
          <g>
            <circle
              cx={width * 0.4}
              cy={arch === "upper" ? -height * 0.3 : -height * 0.3}
              r={5}
              fill={CONDITION_BADGE_COLOR}
              stroke={BG_COLOR}
              strokeWidth={0.8}
            />
            <text
              x={width * 0.4}
              y={arch === "upper" ? -height * 0.3 + 1.5 : -height * 0.3 + 1.5}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-white text-[5px] font-bold font-mono select-none pointer-events-none"
            >
              {conditionCount}
            </text>
          </g>
        )}
      </g>

      {/* FDI number label — counter-rotated so text is always upright */}
      {/* Hidden during hover to avoid duplication with tooltip badge */}
      {!isHovered && (
        <text
          y={fdiLabelY}
          textAnchor="middle"
          transform={`rotate(${-angle})`}
          className="fill-gray-400 text-[7px] font-mono select-none pointer-events-none"
        >
          {toothNumber}
        </text>
      )}

      {/* Hover tooltip — FDI badge with blue background + tooth name */}
      {isHovered && !readOnly && (
        <g transform={`rotate(${-angle})`}>
          {/* Tooltip background */}
          <rect
            x={-52}
            y={tooltipY}
            width={104}
            height={20}
            rx={5}
            fill="#111827"
            stroke="#1F2937"
            strokeWidth={0.6}
            opacity={0.96}
          />

          {/* Tooltip arrow/polygon pointing toward the tooth */}
          {arch === "upper" ? (
            <polygon
              points={`-4,${tooltipY + 20} 4,${tooltipY + 20} 0,${tooltipY + 24}`}
              fill="#111827"
            />
          ) : (
            <polygon
              points={`-4,${tooltipY} 4,${tooltipY} 0,${tooltipY - 4}`}
              fill="#111827"
            />
          )}

          {/* FDI badge (blue rounded rectangle) */}
          <rect
            x={-50}
            y={tooltipY + 3}
            width={20}
            height={14}
            rx={3}
            fill={BADGE_BG_COLOR}
          />
          <text
            x={-40}
            y={tooltipY + 13}
            textAnchor="middle"
            className="fill-white text-[8px] font-bold font-mono select-none pointer-events-none"
          >
            {toothNumber}
          </text>

          {/* Tooth name (truncated to fit) */}
          <text
            x={-26}
            y={tooltipY + 13}
            className="fill-gray-300 text-[5.5px] select-none pointer-events-none"
          >
            {toothName.length > 24
              ? toothName.slice(0, 24) + "\u2026"
              : toothName}
          </text>
        </g>
      )}
    </g>
  );
});

SingleTooth.displayName = "SingleTooth";

// ─── ToothArchSVG Component ──────────────────────────────────────────────────

/**
 * Anatomic arch SVG view of the odontogram.
 * Renders 32 teeth with anatomic shapes (incisors, canines, premolars, molars)
 * positioned along upper and lower dental arches on a dark background.
 * Each tooth shows visible roots, a cervical line, and is colored by its worst
 * zone condition.
 *
 * ViewBox: 520x620 with 80px mouth gap between arches.
 * Labels: Paladar (upper center), Lengua (lower center), Derecho, Izquierdo.
 */
function ToothArchSVG({
  teeth,
  dentitionType,
  selectedTooth,
  onToothClick,
  readOnly = false,
}: ToothArchSVGProps) {
  // Build a lookup map: toothNumber -> ToothData
  const toothMap = React.useMemo(() => {
    const map = new Map<number, ToothData>();
    for (const t of teeth) {
      map.set(t.tooth_number, t);
    }
    return map;
  }, [teeth]);

  // Filter positions by dentition type
  const visiblePositions = React.useMemo(() => {
    if (dentitionType === "adult") {
      const adultSet = new Set(ADULT_TEETH);
      return TOOTH_ARCH_POSITIONS.filter((p) => adultSet.has(p.toothNumber));
    }
    // For pediatric/mixed, show all positions that have tooth data
    return TOOTH_ARCH_POSITIONS.filter((p) => toothMap.has(p.toothNumber));
  }, [dentitionType, toothMap]);

  const {
    viewBoxWidth,
    viewBoxHeight,
    centerX,
    upper,
    lower,
  } = ARCH_GEOMETRY;

  // Vertical center of the mouth gap (between arches)
  const mouthCenterY = (upper.centerY + upper.ry + (lower.centerY - lower.ry)) / 2;

  return (
    <div className="relative w-full bg-gray-950 rounded-2xl overflow-hidden">
      <svg
        viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto"
        role="img"
        aria-label="Odontograma anatómico — vista de arcos dentales"
      >
        {/* Background */}
        <rect width={viewBoxWidth} height={viewBoxHeight} fill={BG_COLOR} rx="16" />

        {/* Arch guide ellipses (subtle dashed outlines) */}
        <ellipse
          cx={centerX}
          cy={upper.centerY}
          rx={upper.rx}
          ry={upper.ry}
          fill="none"
          stroke={GUIDE_STROKE}
          strokeWidth={0.5}
          strokeDasharray="3,6"
          opacity={0.35}
        />
        <ellipse
          cx={centerX}
          cy={lower.centerY}
          rx={lower.rx}
          ry={lower.ry}
          fill="none"
          stroke={GUIDE_STROKE}
          strokeWidth={0.5}
          strokeDasharray="3,6"
          opacity={0.35}
        />

        {/* Center divider line (vertical, separating left/right) */}
        <line
          x1={centerX}
          y1={20}
          x2={centerX}
          y2={viewBoxHeight - 20}
          stroke={GUIDE_STROKE}
          strokeWidth={0.5}
          strokeDasharray="2,5"
          opacity={0.4}
        />

        {/* Anatomical labels */}

        {/* "Paladar" — upper center, inside the upper arch */}
        <text
          x={centerX}
          y={upper.centerY + upper.ry * 0.45}
          textAnchor="middle"
          className="fill-gray-600 text-[10px] italic select-none pointer-events-none"
        >
          Paladar
        </text>

        {/* "Lengua" — lower center, inside the lower arch */}
        <text
          x={centerX}
          y={lower.centerY - lower.ry * 0.45}
          textAnchor="middle"
          className="fill-gray-600 text-[10px] italic select-none pointer-events-none"
        >
          Lengua
        </text>

        {/* "Derecho" — right side (patient's right = viewer's left) */}
        <text
          x={18}
          y={mouthCenterY + 4}
          textAnchor="start"
          className="fill-gray-600 text-[9px] font-medium select-none pointer-events-none"
          style={{ letterSpacing: "0.05em" }}
        >
          Derecho
        </text>

        {/* "Izquierdo" — left side (patient's left = viewer's right) */}
        <text
          x={viewBoxWidth - 18}
          y={mouthCenterY + 4}
          textAnchor="end"
          className="fill-gray-600 text-[9px] font-medium select-none pointer-events-none"
          style={{ letterSpacing: "0.05em" }}
        >
          Izquierdo
        </text>

        {/* Quadrant labels (small, near the corners) */}
        <text
          x={24}
          y={28}
          className="fill-gray-700 text-[7px] font-mono select-none pointer-events-none"
        >
          Q1
        </text>
        <text
          x={viewBoxWidth - 24}
          y={28}
          textAnchor="end"
          className="fill-gray-700 text-[7px] font-mono select-none pointer-events-none"
        >
          Q2
        </text>
        <text
          x={viewBoxWidth - 24}
          y={viewBoxHeight - 18}
          textAnchor="end"
          className="fill-gray-700 text-[7px] font-mono select-none pointer-events-none"
        >
          Q3
        </text>
        <text
          x={24}
          y={viewBoxHeight - 18}
          className="fill-gray-700 text-[7px] font-mono select-none pointer-events-none"
        >
          Q4
        </text>

        {/* Teeth */}
        {visiblePositions.map((position) => (
          <SingleTooth
            key={position.toothNumber}
            position={position}
            toothData={toothMap.get(position.toothNumber)}
            isSelected={selectedTooth === position.toothNumber}
            readOnly={readOnly}
            onToothClick={onToothClick}
          />
        ))}
      </svg>
    </div>
  );
}

ToothArchSVG.displayName = "ToothArchSVG";

export { ToothArchSVG };
