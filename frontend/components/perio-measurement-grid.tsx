"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type PerioSite = "mb" | "b" | "db" | "ml" | "l" | "dl";

export interface PerioMeasurementCell {
  site: PerioSite;
  pocket_depth: number;
  bleeding: boolean;
}

export interface PerioToothRow {
  tooth_number: string;
  measurements: PerioMeasurementCell[];
}

export interface PerioMeasurementGridProps {
  teeth: PerioToothRow[];
  editable?: boolean;
  onCellChange?: (toothNumber: string, site: PerioSite, value: number) => void;
  onBleedingChange?: (toothNumber: string, site: PerioSite, bleeding: boolean) => void;
  className?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SITES: PerioSite[] = ["mb", "b", "db", "ml", "l", "dl"];

const SITE_LABELS: Record<PerioSite, string> = {
  mb: "MB",
  b: "B",
  db: "DB",
  ml: "ML",
  l: "L",
  dl: "DL",
};

// ─── Color coding by depth ────────────────────────────────────────────────────

function depthCellClass(depth: number): string {
  if (depth === 0) return "bg-transparent text-[hsl(var(--muted-foreground))]";
  if (depth <= 3) return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200";
  if (depth <= 5) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200";
  if (depth <= 7) return "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200";
  return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200";
}

// ─── Editable Cell ────────────────────────────────────────────────────────────

interface EditableCellProps {
  value: number;
  bleeding: boolean;
  editable: boolean;
  onChange?: (value: number) => void;
  onBleedingToggle?: () => void;
}

function MeasurementCell({
  value,
  bleeding,
  editable,
  onChange,
  onBleedingToggle,
}: EditableCellProps) {
  const [editing, setEditing] = React.useState(false);
  const [inputVal, setInputVal] = React.useState(String(value || ""));
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  function handleClick() {
    if (!editable) return;
    setEditing(true);
    setInputVal(value > 0 ? String(value) : "");
  }

  function handleBlur() {
    setEditing(false);
    const parsed = parseInt(inputVal, 10);
    if (!isNaN(parsed) && parsed !== value) {
      onChange?.(Math.max(0, Math.min(20, parsed)));
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" || e.key === "Tab") {
      setEditing(false);
      const parsed = parseInt(inputVal, 10);
      if (!isNaN(parsed)) {
        onChange?.(Math.max(0, Math.min(20, parsed)));
      }
    }
    if (e.key === "Escape") {
      setEditing(false);
      setInputVal(String(value || ""));
    }
  }

  if (editing) {
    return (
      <td className="p-0.5 text-center">
        <input
          ref={inputRef}
          type="number"
          min={0}
          max={20}
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          className={cn(
            "w-8 h-8 rounded text-center text-xs font-bold",
            "border-2 border-primary-500 bg-primary-50 dark:bg-primary-900/30",
            "text-foreground focus:outline-none",
          )}
        />
      </td>
    );
  }

  return (
    <td className="p-0.5 text-center">
      <div className="relative inline-flex items-center justify-center">
        <button
          type="button"
          onClick={handleClick}
          className={cn(
            "w-8 h-8 rounded text-xs font-bold transition-colors",
            depthCellClass(value),
            editable && "hover:ring-2 hover:ring-primary-400 cursor-pointer",
            !editable && "cursor-default",
          )}
          title={editable ? `Profundidad: ${value}mm. Clic para editar.` : `${value}mm`}
          disabled={!editable}
        >
          {value > 0 ? value : "—"}
        </button>
        {/* Bleeding indicator */}
        {bleeding && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (editable) onBleedingToggle?.();
            }}
            className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-red-500 border border-white dark:border-zinc-900"
            title="Sangrado al sondaje. Clic para quitar."
            disabled={!editable}
          />
        )}
        {/* Add bleeding when editable and no bleeding */}
        {editable && !bleeding && value > 0 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onBleedingToggle?.();
            }}
            className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-transparent border border-slate-300 dark:border-zinc-600 hover:bg-red-100"
            title="Marcar sangrado"
          />
        )}
      </div>
    </td>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function PerioMeasurementGrid({
  teeth,
  editable = false,
  onCellChange,
  onBleedingChange,
  className,
}: PerioMeasurementGridProps) {
  if (teeth.length === 0) {
    return (
      <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
        Sin mediciones registradas.
      </p>
    );
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="text-xs border-collapse min-w-full">
        <thead>
          <tr>
            <th className="text-left px-2 py-1 text-[hsl(var(--muted-foreground))] font-medium w-14 sticky left-0 bg-[hsl(var(--background))]">
              Diente
            </th>
            {SITES.map((site) => (
              <th
                key={site}
                className="text-center px-0.5 py-1 text-[hsl(var(--muted-foreground))] font-medium w-9"
              >
                {SITE_LABELS[site]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teeth.map((row) => {
            const measureMap = Object.fromEntries(
              row.measurements.map((m) => [m.site, m]),
            ) as Record<PerioSite, PerioMeasurementCell | undefined>;

            return (
              <tr
                key={row.tooth_number}
                className="border-t border-[hsl(var(--border))]"
              >
                {/* Tooth number */}
                <td className="px-2 py-0.5 font-mono font-semibold text-foreground sticky left-0 bg-[hsl(var(--background))]">
                  {row.tooth_number}
                </td>

                {/* Measurements per site */}
                {SITES.map((site) => {
                  const cell = measureMap[site];
                  return (
                    <MeasurementCell
                      key={site}
                      value={cell?.pocket_depth ?? 0}
                      bleeding={cell?.bleeding ?? false}
                      editable={editable}
                      onChange={(v) => onCellChange?.(row.tooth_number, site, v)}
                      onBleedingToggle={() =>
                        onBleedingChange?.(
                          row.tooth_number,
                          site,
                          !(cell?.bleeding ?? false),
                        )
                      }
                    />
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-[hsl(var(--muted-foreground))]">Leyenda:</span>
        {[
          { range: "1–3mm", color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300" },
          { range: "4–5mm", color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300" },
          { range: "6–7mm", color: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300" },
          { range: "8+mm", color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300" },
        ].map((item) => (
          <span
            key={item.range}
            className={cn("px-1.5 py-0.5 rounded font-medium", item.color)}
          >
            {item.range}
          </span>
        ))}
        <span className="flex items-center gap-1 text-[hsl(var(--muted-foreground))]">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />
          Sangrado
        </span>
      </div>
    </div>
  );
}
