"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ToothCell } from "./tooth-cell";
import type { ToothData } from "@/lib/hooks/use-odontogram";
import type { DentitionType } from "@/lib/validations/odontogram";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ToothGridProps {
  /** All teeth with their zone condition data */
  teeth: ToothData[];
  /** Current dentition type: adult, pediatric, or mixed */
  dentitionType: DentitionType;
  /** Currently selected tooth number (null if none) */
  selectedTooth: number | null;
  /** Currently selected zone within the selected tooth */
  selectedZone: string | null;
  /** Callback when a zone on a tooth is clicked */
  onZoneClick: (toothNumber: number, zone: string) => void;
  /** Callback when a tooth number label is clicked */
  onToothClick: (toothNumber: number) => void;
  /** Whether the grid is in read-only mode (no odontogram:write permission) */
  readOnly?: boolean;
}

// ─── FDI Tooth Number Layout ─────────────────────────────────────────────────

/**
 * Adult teeth arranged by quadrant in display order.
 *
 * Upper jaw (left-to-right as seen by observer facing the patient):
 *   Q1 (upper right): 18..11  |  Q2 (upper left): 21..28
 *
 * Lower jaw (left-to-right):
 *   Q4 (lower right): 48..41  |  Q3 (lower left): 31..38
 */
const ADULT_UPPER_RIGHT: readonly number[] = [18, 17, 16, 15, 14, 13, 12, 11];
const ADULT_UPPER_LEFT: readonly number[] = [21, 22, 23, 24, 25, 26, 27, 28];
const ADULT_LOWER_RIGHT: readonly number[] = [48, 47, 46, 45, 44, 43, 42, 41];
const ADULT_LOWER_LEFT: readonly number[] = [31, 32, 33, 34, 35, 36, 37, 38];

/**
 * Pediatric teeth arranged by quadrant in display order.
 */
const PEDIATRIC_UPPER_RIGHT: readonly number[] = [55, 54, 53, 52, 51];
const PEDIATRIC_UPPER_LEFT: readonly number[] = [61, 62, 63, 64, 65];
const PEDIATRIC_LOWER_RIGHT: readonly number[] = [85, 84, 83, 82, 81];
const PEDIATRIC_LOWER_LEFT: readonly number[] = [71, 72, 73, 74, 75];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Returns the tooth data for a given tooth number from the teeth array.
 * Falls back to an empty tooth if not found in the data.
 */
function getToothData(teeth: ToothData[], toothNumber: number): ToothData {
  return (
    teeth.find((t) => t.tooth_number === toothNumber) ?? {
      tooth_number: toothNumber,
      zones: [],
      history_count: 0,
    }
  );
}

// ─── Quadrant Row Sub-component ──────────────────────────────────────────────

interface QuadrantRowProps {
  /** Left quadrant tooth numbers (displayed from left to midline) */
  leftTeeth: readonly number[];
  /** Right quadrant tooth numbers (displayed from midline to right) */
  rightTeeth: readonly number[];
  /** All teeth data */
  teeth: ToothData[];
  /** Currently selected tooth */
  selectedTooth: number | null;
  /** Currently selected zone */
  selectedZone: string | null;
  onZoneClick: (toothNumber: number, zone: string) => void;
  onToothClick: (toothNumber: number) => void;
  readOnly: boolean;
  /** Label for left quadrant (e.g. "Q1") */
  leftLabel: string;
  /** Label for right quadrant (e.g. "Q2") */
  rightLabel: string;
}

function QuadrantRow({
  leftTeeth,
  rightTeeth,
  teeth,
  selectedTooth,
  selectedZone,
  onZoneClick,
  onToothClick,
  readOnly,
  leftLabel,
  rightLabel,
}: QuadrantRowProps) {
  return (
    <div className="flex items-center gap-0.5">
      {/* Left quadrant label */}
      <span className="w-8 shrink-0 text-[10px] font-bold text-[hsl(var(--muted-foreground))] text-center">
        {leftLabel}
      </span>

      {/* Left quadrant teeth */}
      <div className="flex items-end gap-0.5">
        {leftTeeth.map((tn) => {
          const data = getToothData(teeth, tn);
          return (
            <ToothCell
              key={tn}
              toothNumber={tn}
              zones={data.zones}
              isSelected={selectedTooth === tn}
              selectedZone={selectedTooth === tn ? selectedZone : null}
              onZoneClick={onZoneClick}
              onToothClick={onToothClick}
              readOnly={readOnly}
            />
          );
        })}
      </div>

      {/* Midline separator */}
      <div className="mx-1 h-16 w-px bg-[hsl(var(--border))] shrink-0" />

      {/* Right quadrant teeth */}
      <div className="flex items-end gap-0.5">
        {rightTeeth.map((tn) => {
          const data = getToothData(teeth, tn);
          return (
            <ToothCell
              key={tn}
              toothNumber={tn}
              zones={data.zones}
              isSelected={selectedTooth === tn}
              selectedZone={selectedTooth === tn ? selectedZone : null}
              onZoneClick={onZoneClick}
              onToothClick={onToothClick}
              readOnly={readOnly}
            />
          );
        })}
      </div>

      {/* Right quadrant label */}
      <span className="w-8 shrink-0 text-[10px] font-bold text-[hsl(var(--muted-foreground))] text-center">
        {rightLabel}
      </span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * The main odontogram grid showing all teeth arranged by quadrant.
 *
 * Layout (classic dental chart, observer facing patient):
 *
 * ADULT:
 *   Q1: 18..11 | 21..28 :Q2   (upper jaw)
 *   ────────── midline ──────────
 *   Q4: 48..41 | 31..38 :Q3   (lower jaw)
 *
 * PEDIATRIC:
 *   Q5: 55..51 | 61..65 :Q6   (upper jaw)
 *   ────────── midline ──────────
 *   Q8: 85..81 | 71..75 :Q7   (lower jaw)
 *
 * MIXED: both adult and pediatric rows are shown.
 */
function ToothGrid({
  teeth,
  dentitionType,
  selectedTooth,
  selectedZone,
  onZoneClick,
  onToothClick,
  readOnly = false,
}: ToothGridProps) {
  const showAdult = dentitionType === "adult" || dentitionType === "mixed";
  const showPediatric = dentitionType === "pediatric" || dentitionType === "mixed";

  return (
    <div
      className="overflow-x-auto"
      role="region"
      aria-label="Odontograma dental"
    >
      <div className="inline-flex flex-col items-center gap-2 min-w-fit p-4">
        {/* ── Upper Jaw ────────────────────────────────────────────────── */}

        {showAdult && (
          <QuadrantRow
            leftTeeth={ADULT_UPPER_RIGHT}
            rightTeeth={ADULT_UPPER_LEFT}
            teeth={teeth}
            selectedTooth={selectedTooth}
            selectedZone={selectedZone}
            onZoneClick={onZoneClick}
            onToothClick={onToothClick}
            readOnly={readOnly}
            leftLabel="Q1"
            rightLabel="Q2"
          />
        )}

        {showPediatric && (
          <QuadrantRow
            leftTeeth={PEDIATRIC_UPPER_RIGHT}
            rightTeeth={PEDIATRIC_UPPER_LEFT}
            teeth={teeth}
            selectedTooth={selectedTooth}
            selectedZone={selectedZone}
            onZoneClick={onZoneClick}
            onToothClick={onToothClick}
            readOnly={readOnly}
            leftLabel="Q5"
            rightLabel="Q6"
          />
        )}

        {/* ── Jaw Separator ────────────────────────────────────────────── */}
        <div className="flex items-center w-full gap-2 my-1">
          <div className="flex-1 h-px bg-[hsl(var(--border))]" />
          <span className="text-[10px] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider px-2">
            Linea media
          </span>
          <div className="flex-1 h-px bg-[hsl(var(--border))]" />
        </div>

        {/* ── Lower Jaw ────────────────────────────────────────────────── */}

        {showPediatric && (
          <QuadrantRow
            leftTeeth={PEDIATRIC_LOWER_RIGHT}
            rightTeeth={PEDIATRIC_LOWER_LEFT}
            teeth={teeth}
            selectedTooth={selectedTooth}
            selectedZone={selectedZone}
            onZoneClick={onZoneClick}
            onToothClick={onToothClick}
            readOnly={readOnly}
            leftLabel="Q8"
            rightLabel="Q7"
          />
        )}

        {showAdult && (
          <QuadrantRow
            leftTeeth={ADULT_LOWER_RIGHT}
            rightTeeth={ADULT_LOWER_LEFT}
            teeth={teeth}
            selectedTooth={selectedTooth}
            selectedZone={selectedZone}
            onZoneClick={onZoneClick}
            onToothClick={onToothClick}
            readOnly={readOnly}
            leftLabel="Q4"
            rightLabel="Q3"
          />
        )}
      </div>
    </div>
  );
}

ToothGrid.displayName = "ToothGrid";

export { ToothGrid };
