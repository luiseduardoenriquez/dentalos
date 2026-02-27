"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { ZoneData } from "@/lib/hooks/use-odontogram";
import { getZoneLabel } from "@/lib/odontogram/zone-helpers";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ZoneChipsProps {
  /** Zone data for the current tooth */
  zones: ZoneData[];
  /** Optional callback when a chip is clicked (selects that zone) */
  onChipClick?: (zone: string) => void;
  /** Currently selected zone (highlights the chip) */
  selectedZone?: string | null;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Horizontal list of badge chips for zones that have conditions.
 * Each chip shows [ZoneName]: [ConditionName] with a color dot.
 * Empty zones are not shown. When all zones are healthy, shows "Sin hallazgos".
 */
function ZoneChips({ zones, onChipClick, selectedZone }: ZoneChipsProps) {
  const zonesWithConditions = zones.filter(
    (z) => z.condition !== null && z.condition !== undefined,
  );

  if (zonesWithConditions.length === 0) {
    return (
      <p className="text-xs text-gray-500 italic">Sin hallazgos</p>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {zonesWithConditions.map((zone) => {
        const isSelected = selectedZone === zone.zone;
        return (
          <button
            key={zone.zone}
            type="button"
            onClick={() => onChipClick?.(zone.zone)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1",
              "text-xs font-medium transition-all duration-100",
              "border",
              isSelected
                ? "border-blue-500 bg-blue-500/10 text-blue-300"
                : "border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500",
              onChipClick ? "cursor-pointer" : "cursor-default",
            )}
          >
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{
                backgroundColor:
                  zone.condition?.condition_color ?? "#6B7280",
              }}
              aria-hidden="true"
            />
            <span>
              {getZoneLabel(zone.zone)}
              {zone.condition?.condition_name && (
                <span className="text-gray-400">
                  : {zone.condition.condition_name}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}

ZoneChips.displayName = "ZoneChips";

export { ZoneChips };
