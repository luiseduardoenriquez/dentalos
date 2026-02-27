/**
 * Shared zone SVG helpers extracted from tooth-cell.tsx.
 * Used by both the classic ToothCell and the anatomic ToothDetailModal.
 */

import type { ZoneData } from "@/lib/hooks/use-odontogram";
import { isAnteriorTooth, ZONE_LABELS } from "@/lib/validations/odontogram";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Default zone fill when no condition is present. */
export const EMPTY_FILL = "#FFFFFF";
export const EMPTY_FILL_DARK = "#374151"; // gray-700 for dark mode
export const EMPTY_STROKE = "#CBD5E1"; // slate-300
export const EMPTY_STROKE_DARK = "#6B7280"; // gray-500 for dark mode
export const CONDITION_STROKE = "#94A3B8"; // slate-400
export const SELECTED_STROKE = "#2563EB"; // primary-600

/**
 * SVG polygon points for each zone within a 56×56 viewBox.
 * Crown area occupies the top 40px, root extends below.
 *
 * Layout (cross-shape):
 *          [vestibular]
 *   [mesial] [center] [distal]
 *          [lingual]
 *            [root]
 */
export const ZONE_POLYGONS = {
  top: "14,0 42,0 35,14 21,14",
  bottom: "21,26 35,26 42,40 14,40",
  left: "0,0 14,0 21,14 21,26 14,40 0,40",
  right: "42,0 56,0 56,40 42,40 35,26 35,14",
  center: "21,14 35,14 35,26 21,26",
  root: "18,43 38,43 38,56 18,56",
} as const;

export type ZonePosition = keyof typeof ZONE_POLYGONS;

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
export function getZonePositionMap(
  toothNumber: number,
): Record<string, string> {
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
 * @param darkMode - When true, returns gray-700 instead of white for empty zones
 */
export function getZoneFill(
  zones: ZoneData[],
  zoneName: string,
  darkMode = false,
): string {
  const zoneData = zones.find((z) => z.zone === zoneName);
  if (zoneData?.condition?.condition_color) {
    return zoneData.condition.condition_color;
  }
  return darkMode ? EMPTY_FILL_DARK : EMPTY_FILL;
}

/**
 * Checks if a zone has an active condition.
 */
export function zoneHasCondition(zones: ZoneData[], zoneName: string): boolean {
  const zoneData = zones.find((z) => z.zone === zoneName);
  return zoneData?.condition !== null && zoneData?.condition !== undefined;
}

/**
 * Gets the "worst" (most severe) condition color from all zones of a tooth.
 * Returns the first non-null condition color found, or null if all zones are healthy.
 * Used by the arch view to color the entire tooth rectangle.
 */
export function getWorstZoneColor(zones: ZoneData[]): string | null {
  for (const zone of zones) {
    if (zone.condition?.condition_color) {
      return zone.condition.condition_color;
    }
  }
  return null;
}

/**
 * Counts how many zones have conditions on a tooth.
 */
export function countConditions(zones: ZoneData[]): number {
  return zones.filter(
    (z) => z.condition !== null && z.condition !== undefined,
  ).length;
}

/**
 * Gets zone label in Spanish.
 */
export function getZoneLabel(zoneName: string): string {
  return ZONE_LABELS[zoneName] ?? zoneName;
}
