"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  FACIAL_ZONES,
  ZONES_BY_ID,
  INJECTION_TYPE_COLORS,
} from "@/lib/facial-aesthetics/zones";
import type { InjectionResponse } from "@/lib/hooks/use-facial-aesthetics";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FaceDiagramSVGProps {
  /** Current injection data for this session */
  injections: InjectionResponse[];
  /** Callback when a zone marker is clicked */
  onZoneClick: (zoneId: string) => void;
  /** Currently selected zone id (null if none) */
  selectedZone: string | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const VIEW_W = 400;
const VIEW_H = 560;
const BG_COLOR = "#1E293B"; // slate-800 — dark theme background
const GUIDE_STROKE = "#334155"; // slate-700
const LABEL_COLOR = "#475569"; // slate-600
const ZONE_EMPTY_STROKE = "#4B5563"; // gray-600 — outline-only for empty zones
const ZONE_EMPTY_FILL = "transparent";
const ZONE_RADIUS = 7; // visual circle radius
const ZONE_HIT_RADIUS = 22; // invisible hit area radius (ensures 44px touch target)
const SELECTED_STROKE = "#38BDF8"; // sky-400

// ─── Face outline paths ───────────────────────────────────────────────────────
//
// Medical diagram style front-view face silhouette.
// All coordinates are in the 400x560 viewBox space.
// The face is centered horizontally at x=200.
// Head occupies roughly y=30 to y=390; neck y=390 to y=500.

/** Outer head/jaw oval outline */
const FACE_OUTLINE = `
  M 200,32
  C 270,32 320,70 330,120
  C 342,175 340,230 332,280
  C 324,325 308,358 290,375
  C 278,386 268,392 256,395
  C 248,400 230,405 200,406
  C 170,405 152,400 144,395
  C 132,392 122,386 110,375
  C 92,358 76,325 68,280
  C 60,230 58,175 70,120
  C 80,70 130,32 200,32
  Z
`;

/** Left eyebrow arc */
const EYEBROW_LEFT = `M 140,148 Q 155,138 172,146`;
/** Right eyebrow arc */
const EYEBROW_RIGHT = `M 228,146 Q 245,138 260,148`;

/** Left eye ellipse (rx=18, ry=9) centered at (156, 163) */
const EYE_LEFT_CX = 156;
const EYE_LEFT_CY = 163;
const EYE_LEFT_RX = 18;
const EYE_LEFT_RY = 9;

/** Right eye ellipse (rx=18, ry=9) centered at (244, 163) */
const EYE_RIGHT_CX = 244;
const EYE_RIGHT_CY = 163;
const EYE_RIGHT_RX = 18;
const EYE_RIGHT_RY = 9;

/** Nose — simple triangle-ish outline with nostrils */
const NOSE_PATH = `
  M 200,196
  L 190,250 Q 186,256 182,258 Q 178,261 178,264
  Q 178,268 186,268 L 200,265 L 214,268
  Q 222,268 222,264
  Q 222,261 218,258 Q 214,256 210,250
  Z
`;

/** Upper lip */
const LIP_UPPER = `
  M 174,298
  Q 184,292 194,295 Q 200,297 206,295 Q 216,292 226,298
  Q 218,305 200,304 Q 182,305 174,298
  Z
`;

/** Lower lip */
const LIP_LOWER = `
  M 174,298
  Q 182,318 200,320 Q 218,318 226,298
  Q 218,305 200,304 Q 182,305 174,298
  Z
`;

/** Neck outline — two angled lines from jaw base downward */
const NECK_LEFT = `M 175,406 L 168,490 L 215,490`;
const NECK_RIGHT = `M 225,406 L 232,490 L 185,490`;

/** Hairline curve — gentle arc across the top of the forehead */
const HAIRLINE = `M 120,98 Q 200,68 280,98`;

/** Nasolabial fold lines */
const NASOLABIAL_LEFT = `M 176,258 Q 166,280 170,300`;
const NASOLABIAL_RIGHT = `M 224,258 Q 234,280 230,300`;

// ─── ZoneMarker (memoized) ────────────────────────────────────────────────────

interface ZoneMarkerProps {
  zoneId: string;
  cx: number;
  cy: number;
  label: string;
  injection: InjectionResponse | undefined;
  isSelected: boolean;
  onZoneClick: (zoneId: string) => void;
}

const ZoneMarker = React.memo(function ZoneMarker({
  zoneId,
  cx,
  cy,
  label,
  injection,
  isSelected,
  onZoneClick,
}: ZoneMarkerProps) {
  const [isHovered, setIsHovered] = React.useState(false);

  const isFilled = Boolean(injection);

  // Resolve fill color
  const fillColor = isFilled
    ? (INJECTION_TYPE_COLORS[injection!.injection_type] ?? INJECTION_TYPE_COLORS.other)
    : ZONE_EMPTY_FILL;

  // Resolve stroke color
  const strokeColor = isSelected
    ? SELECTED_STROKE
    : isFilled
      ? (INJECTION_TYPE_COLORS[injection!.injection_type] ?? INJECTION_TYPE_COLORS.other)
      : ZONE_EMPTY_STROKE;

  const strokeWidth = isSelected ? 2.5 : isFilled ? 1.5 : 1.5;

  // Tooltip: place above the marker unless it's near the top (y < 100)
  const tooltipAbove = cy > 100;
  const tooltipY = tooltipAbove ? cy - ZONE_RADIUS - 28 : cy + ZONE_RADIUS + 8;
  const tooltipLineY = tooltipAbove ? cy - ZONE_RADIUS - 2 : cy + ZONE_RADIUS + 2;

  // Clamp tooltip x so it doesn't overflow viewBox
  const tooltipW = 148;
  const tooltipX = Math.min(Math.max(cx - tooltipW / 2, 4), VIEW_W - tooltipW - 4);

  return (
    <g
      role="button"
      aria-label={`${label}${isFilled ? ` — ${injection!.injection_type}` : ""}`}
      tabIndex={0}
      style={{ cursor: "pointer" }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onZoneClick(zoneId)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onZoneClick(zoneId);
        }
      }}
    >
      {/* Invisible expanded hit area — ensures 44px minimum touch target */}
      <circle
        cx={cx}
        cy={cy}
        r={ZONE_HIT_RADIUS}
        fill="transparent"
        aria-hidden="true"
      />

      {/* Pulsing selection ring — only visible when this zone is selected */}
      {isSelected && (
        <circle
          cx={cx}
          cy={cy}
          r={ZONE_RADIUS + 5}
          fill="none"
          stroke={SELECTED_STROKE}
          strokeWidth={1.5}
          opacity={0.7}
          className="animate-pulse"
          style={{
            filter: `drop-shadow(0 0 6px ${SELECTED_STROKE})`,
          }}
          aria-hidden="true"
        />
      )}

      {/* Hover ring — subtle glow on hover for non-selected zones */}
      {isHovered && !isSelected && (
        <circle
          cx={cx}
          cy={cy}
          r={ZONE_RADIUS + 4}
          fill="none"
          stroke={isFilled ? strokeColor : ZONE_EMPTY_STROKE}
          strokeWidth={1}
          opacity={0.45}
          aria-hidden="true"
        />
      )}

      {/* Main zone circle — filled if injection data exists, outline if empty */}
      <circle
        cx={cx}
        cy={cy}
        r={ZONE_RADIUS}
        fill={fillColor}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        opacity={isFilled ? 0.9 : 0.6}
        className="transition-opacity duration-150"
        style={
          isFilled
            ? { filter: `drop-shadow(0 0 3px ${strokeColor}40)` }
            : undefined
        }
      />

      {/* Inner dot — shown on filled zones to distinguish from outline circles */}
      {isFilled && (
        <circle
          cx={cx}
          cy={cy}
          r={2.5}
          fill="white"
          opacity={0.8}
          aria-hidden="true"
        />
      )}

      {/* Tooltip — shown on hover */}
      {isHovered && (
        <g aria-hidden="true">
          {/* Connector tick */}
          <line
            x1={cx}
            y1={tooltipLineY}
            x2={cx}
            y2={tooltipAbove ? tooltipY + 18 : tooltipY}
            stroke="#1E3A5F"
            strokeWidth={1}
            opacity={0.6}
          />

          {/* Tooltip background */}
          <rect
            x={tooltipX}
            y={tooltipY}
            width={tooltipW}
            height={20}
            rx={4}
            fill="#0F172A"
            stroke="#334155"
            strokeWidth={0.75}
            opacity={0.97}
          />

          {/* Tooltip text — zone label */}
          <text
            x={tooltipX + 8}
            y={tooltipY + 13}
            className="select-none pointer-events-none"
            style={{
              fontSize: "9px",
              fill: isFilled ? strokeColor : "#94A3B8",
              fontFamily: "sans-serif",
            }}
          >
            {label}
            {isFilled && (
              <tspan fill="#64748B"> — {injection!.injection_type.replace(/_/g, " ")}</tspan>
            )}
          </text>
        </g>
      )}
    </g>
  );
});

ZoneMarker.displayName = "ZoneMarker";

// ─── FaceDiagramSVG Component ─────────────────────────────────────────────────

/**
 * Interactive face diagram SVG for plotting facial injection points.
 * Renders a front-view medical diagram of a face with ~28 clickable zone
 * markers. Each marker is colored by injection type when a treatment has been
 * recorded, or shown as an outline circle when the zone is empty.
 *
 * ViewBox: 400x560 — dark slate background (#1E293B).
 * All labels in Spanish (es-419).
 *
 * Follows the same interactive pattern as ToothArchSVG:
 * - Selected zone gets a pulsing ring animation
 * - Hovering shows a tooltip with zone name and injection type
 * - Touch targets are always at least 44px (invisible hitbox circle)
 */
function FaceDiagramSVG({
  injections,
  onZoneClick,
  selectedZone,
}: FaceDiagramSVGProps) {
  // Build a lookup map: zone_id → InjectionResponse (first injection per zone)
  const injectionByZone = React.useMemo(() => {
    const map = new Map<string, InjectionResponse>();
    for (const inj of injections) {
      // Keep the most recently updated injection per zone if multiple exist
      const existing = map.get(inj.zone_id);
      if (!existing || inj.updated_at > existing.updated_at) {
        map.set(inj.zone_id, inj);
      }
    }
    return map;
  }, [injections]);

  return (
    <div
      className={cn(
        "relative w-full rounded-2xl overflow-hidden",
        "bg-slate-800", // matches BG_COLOR
      )}
    >
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto"
        role="img"
        aria-label="Diagrama facial — vista frontal para registro de inyecciones"
      >
        {/* ── Background ────────────────────────────────────────────────────── */}
        <rect width={VIEW_W} height={VIEW_H} fill={BG_COLOR} rx="16" />

        {/* ── Subtle center guide line (vertical midline) ────────────────── */}
        <line
          x1={VIEW_W / 2}
          y1={20}
          x2={VIEW_W / 2}
          y2={VIEW_H - 20}
          stroke={GUIDE_STROKE}
          strokeWidth={0.5}
          strokeDasharray="2,6"
          opacity={0.4}
        />

        {/* ── Face Anatomy ───────────────────────────────────────────────── */}

        {/* Neck */}
        <path
          d={NECK_LEFT}
          fill="none"
          stroke={GUIDE_STROKE}
          strokeWidth={1.5}
          strokeLinejoin="round"
          opacity={0.7}
        />
        <path
          d={NECK_RIGHT}
          fill="none"
          stroke={GUIDE_STROKE}
          strokeWidth={1.5}
          strokeLinejoin="round"
          opacity={0.7}
        />

        {/* Outer head oval — filled with a very dark slate so the face reads as
            a solid shape, with a slightly lighter stroke for the silhouette */}
        <path
          d={FACE_OUTLINE}
          fill="#243044"
          stroke="#3B5068"
          strokeWidth={1.5}
        />

        {/* Hairline arc — thin dashed line suggesting the top of the hairline */}
        <path
          d={HAIRLINE}
          fill="none"
          stroke={GUIDE_STROKE}
          strokeWidth={1}
          strokeDasharray="3,4"
          opacity={0.5}
        />

        {/* Eyebrows */}
        <path
          d={EYEBROW_LEFT}
          fill="none"
          stroke="#64748B"
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        <path
          d={EYEBROW_RIGHT}
          fill="none"
          stroke="#64748B"
          strokeWidth={2.5}
          strokeLinecap="round"
        />

        {/* Left eye */}
        <ellipse
          cx={EYE_LEFT_CX}
          cy={EYE_LEFT_CY}
          rx={EYE_LEFT_RX}
          ry={EYE_LEFT_RY}
          fill="#1E293B"
          stroke="#64748B"
          strokeWidth={1.2}
        />
        {/* Left iris */}
        <circle cx={EYE_LEFT_CX} cy={EYE_LEFT_CY} r={5} fill="#334155" />

        {/* Right eye */}
        <ellipse
          cx={EYE_RIGHT_CX}
          cy={EYE_RIGHT_CY}
          rx={EYE_RIGHT_RX}
          ry={EYE_RIGHT_RY}
          fill="#1E293B"
          stroke="#64748B"
          strokeWidth={1.2}
        />
        {/* Right iris */}
        <circle cx={EYE_RIGHT_CX} cy={EYE_RIGHT_CY} r={5} fill="#334155" />

        {/* Nose */}
        <path
          d={NOSE_PATH}
          fill="#1E293B"
          stroke="#64748B"
          strokeWidth={1.2}
          strokeLinejoin="round"
        />

        {/* Nasolabial fold lines */}
        <path
          d={NASOLABIAL_LEFT}
          fill="none"
          stroke="#475569"
          strokeWidth={1}
          strokeLinecap="round"
          opacity={0.6}
        />
        <path
          d={NASOLABIAL_RIGHT}
          fill="none"
          stroke="#475569"
          strokeWidth={1}
          strokeLinecap="round"
          opacity={0.6}
        />

        {/* Upper lip */}
        <path
          d={LIP_UPPER}
          fill="#2D3F55"
          stroke="#64748B"
          strokeWidth={1}
          strokeLinejoin="round"
        />

        {/* Lower lip */}
        <path
          d={LIP_LOWER}
          fill="#2D3F55"
          stroke="#64748B"
          strokeWidth={1}
          strokeLinejoin="round"
        />

        {/* ── Anatomical labels ─────────────────────────────────────────── */}

        {/* "Derecho" — patient's right side (viewer's left) */}
        <text
          x={16}
          y={215}
          textAnchor="start"
          style={{
            fontSize: "8px",
            fill: LABEL_COLOR,
            fontFamily: "sans-serif",
            letterSpacing: "0.05em",
          }}
          className="select-none pointer-events-none"
        >
          Derecho
        </text>

        {/* "Izquierdo" — patient's left side (viewer's right) */}
        <text
          x={VIEW_W - 16}
          y={215}
          textAnchor="end"
          style={{
            fontSize: "8px",
            fill: LABEL_COLOR,
            fontFamily: "sans-serif",
            letterSpacing: "0.05em",
          }}
          className="select-none pointer-events-none"
        >
          Izquierdo
        </text>

        {/* ── Zone markers ─────────────────────────────────────────────── */}
        {FACIAL_ZONES.map((zone) => {
          const cx = zone.x * VIEW_W;
          const cy = zone.y * VIEW_H;
          const injection = injectionByZone.get(zone.id);
          const isSelected = selectedZone === zone.id;

          return (
            <ZoneMarker
              key={zone.id}
              zoneId={zone.id}
              cx={cx}
              cy={cy}
              label={zone.label}
              injection={injection}
              isSelected={isSelected}
              onZoneClick={onZoneClick}
            />
          );
        })}
      </svg>
    </div>
  );
}

FaceDiagramSVG.displayName = "FaceDiagramSVG";

export { FaceDiagramSVG };
