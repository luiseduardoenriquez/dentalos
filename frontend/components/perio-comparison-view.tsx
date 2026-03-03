"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

export type PerioSite = "mb" | "b" | "db" | "ml" | "l" | "dl";

export interface PerioComparisonMeasurement {
  site: PerioSite;
  pocket_depth: number;
  bleeding: boolean;
}

export interface PerioComparisonTooth {
  tooth_number: string;
  measurements: PerioComparisonMeasurement[];
}

export interface PerioRecordSnapshot {
  id: string;
  recorded_at: string;
  recorded_by_name: string;
  teeth: PerioComparisonTooth[];
}

export interface PerioComparisonViewProps {
  recordA: PerioRecordSnapshot;
  recordB: PerioRecordSnapshot;
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

// ─── Delta classification ─────────────────────────────────────────────────────

type DeltaStatus = "improved" | "worsened" | "unchanged";

function getDeltaStatus(depthA: number, depthB: number): DeltaStatus {
  if (depthB < depthA) return "improved";
  if (depthB > depthA) return "worsened";
  return "unchanged";
}

function deltaCellClass(status: DeltaStatus): string {
  switch (status) {
    case "improved":
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200";
    case "worsened":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200";
    case "unchanged":
      return "bg-slate-50 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400";
  }
}

// ─── Summary stats ────────────────────────────────────────────────────────────

function computeSummary(
  recordA: PerioRecordSnapshot,
  recordB: PerioRecordSnapshot,
): { improved: number; worsened: number; unchanged: number } {
  let improved = 0;
  let worsened = 0;
  let unchanged = 0;

  for (const toothB of recordB.teeth) {
    const toothA = recordA.teeth.find((t) => t.tooth_number === toothB.tooth_number);
    if (!toothA) continue;

    for (const mB of toothB.measurements) {
      const mA = toothA.measurements.find((m) => m.site === mB.site);
      if (!mA) continue;

      const status = getDeltaStatus(mA.pocket_depth, mB.pocket_depth);
      if (status === "improved") improved++;
      else if (status === "worsened") worsened++;
      else unchanged++;
    }
  }

  return { improved, worsened, unchanged };
}

// ─── Comparison Table ─────────────────────────────────────────────────────────

function ComparisonTable({
  recordA,
  recordB,
}: {
  recordA: PerioRecordSnapshot;
  recordB: PerioRecordSnapshot;
}) {
  const toothNumbers = [
    ...new Set([
      ...recordA.teeth.map((t) => t.tooth_number),
      ...recordB.teeth.map((t) => t.tooth_number),
    ]),
  ].sort();

  return (
    <div className="overflow-x-auto">
      <table className="text-xs w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left px-2 py-1.5 text-[hsl(var(--muted-foreground))] font-medium w-14 border-b border-[hsl(var(--border))]">
              Diente
            </th>
            {SITES.map((site) => (
              <th
                key={site}
                className="text-center px-1 py-1.5 text-[hsl(var(--muted-foreground))] font-medium w-10 border-b border-[hsl(var(--border))]"
              >
                {SITE_LABELS[site]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {toothNumbers.map((tooth) => {
            const toothA = recordA.teeth.find((t) => t.tooth_number === tooth);
            const toothB = recordB.teeth.find((t) => t.tooth_number === tooth);

            const mapA: Record<string, PerioComparisonMeasurement> = {};
            const mapB: Record<string, PerioComparisonMeasurement> = {};

            for (const m of toothA?.measurements ?? []) mapA[m.site] = m;
            for (const m of toothB?.measurements ?? []) mapB[m.site] = m;

            return (
              <tr
                key={tooth}
                className="border-t border-[hsl(var(--border))]"
              >
                <td className="px-2 py-0.5 font-mono font-semibold text-foreground">
                  {tooth}
                </td>
                {SITES.map((site) => {
                  const mA = mapA[site];
                  const mB = mapB[site];

                  if (!mA && !mB) {
                    return (
                      <td key={site} className="text-center px-1 py-0.5">
                        <span className="text-[hsl(var(--muted-foreground))]">—</span>
                      </td>
                    );
                  }

                  const depthA = mA?.pocket_depth ?? 0;
                  const depthB = mB?.pocket_depth ?? 0;
                  const status = getDeltaStatus(depthA, depthB);
                  const delta = depthB - depthA;

                  return (
                    <td key={site} className="text-center px-0.5 py-0.5">
                      <div className="flex flex-col items-center gap-0.5">
                        {/* B value with delta color */}
                        <span
                          className={cn(
                            "w-8 h-7 rounded inline-flex items-center justify-center font-bold",
                            deltaCellClass(status),
                          )}
                          title={`${recordA.recorded_at}: ${depthA}mm → ${recordB.recorded_at}: ${depthB}mm`}
                        >
                          {depthB > 0 ? depthB : "—"}
                        </span>
                        {/* Delta indicator */}
                        {status !== "unchanged" && (
                          <span
                            className={cn(
                              "text-[9px] font-medium flex items-center gap-0.5",
                              status === "improved"
                                ? "text-green-600 dark:text-green-400"
                                : "text-red-600 dark:text-red-400",
                            )}
                          >
                            {status === "improved" ? (
                              <TrendingDown className="h-2.5 w-2.5" />
                            ) : (
                              <TrendingUp className="h-2.5 w-2.5" />
                            )}
                            {Math.abs(delta)}
                          </span>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function PerioComparisonView({
  recordA,
  recordB,
  className,
}: PerioComparisonViewProps) {
  const summary = React.useMemo(
    () => computeSummary(recordA, recordB),
    [recordA, recordB],
  );

  return (
    <div className={cn("space-y-4", className)}>
      {/* ─── Record headers ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 text-xs">
        <div className="rounded-lg border border-[hsl(var(--border))] px-3 py-2">
          <p className="font-medium text-[hsl(var(--muted-foreground))]">Registro A (base)</p>
          <p className="font-semibold text-foreground">{formatDate(recordA.recorded_at)}</p>
          <p className="text-[hsl(var(--muted-foreground))]">{recordA.recorded_by_name}</p>
        </div>
        <div className="rounded-lg border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/10 px-3 py-2">
          <p className="font-medium text-primary-600 dark:text-primary-400">Registro B (actual)</p>
          <p className="font-semibold text-foreground">{formatDate(recordB.recorded_at)}</p>
          <p className="text-[hsl(var(--muted-foreground))]">{recordB.recorded_by_name}</p>
        </div>
      </div>

      {/* ─── Summary stats ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5 text-green-600 dark:text-green-400">
          <TrendingDown className="h-3.5 w-3.5" />
          <span className="font-semibold">{summary.improved}</span>
          <span className="text-[hsl(var(--muted-foreground))]">mejoradas</span>
        </div>
        <div className="flex items-center gap-1.5 text-red-600 dark:text-red-400">
          <TrendingUp className="h-3.5 w-3.5" />
          <span className="font-semibold">{summary.worsened}</span>
          <span className="text-[hsl(var(--muted-foreground))]">empeoradas</span>
        </div>
        <div className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))]">
          <Minus className="h-3.5 w-3.5" />
          <span className="font-semibold">{summary.unchanged}</span>
          <span>sin cambio</span>
        </div>
      </div>

      {/* ─── Comparison table ─────────────────────────────────────────────── */}
      <ComparisonTable recordA={recordA} recordB={recordB} />

      {/* ─── Legend ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-3 text-xs">
        <span className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))]">
          Color de celda:
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-green-100 dark:bg-green-900/30 inline-block" />
          Mejorada
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-red-100 dark:bg-red-900/30 inline-block" />
          Empeorada
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-slate-50 dark:bg-zinc-800 inline-block" />
          Sin cambio
        </span>
      </div>
    </div>
  );
}
