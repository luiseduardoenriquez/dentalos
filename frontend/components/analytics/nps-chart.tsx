"use client";

import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface NpsTrendPoint {
  period: string;
  nps_score: number;
  responses: number;
}

interface NpsChartProps {
  trend: NpsTrendPoint[];
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function npsBarColor(score: number): string {
  if (score > 30) return "bg-green-500";
  if (score >= 0) return "bg-yellow-400";
  return "bg-red-500";
}

function npsLabelColor(score: number): string {
  if (score > 30) return "text-green-600 dark:text-green-400";
  if (score >= 0) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

// For display, clamp score -100..100 to 0..100 height %
function barHeightPct(score: number): number {
  // Map -100..100 to 0..100 for bar height
  return Math.max(4, ((score + 100) / 200) * 100);
}

// ─── Component ────────────────────────────────────────────────────────────────

export function NpsChart({ trend, className }: NpsChartProps) {
  if (!trend || trend.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center h-40 rounded-lg border border-dashed border-[hsl(var(--border))] text-sm text-[hsl(var(--muted-foreground))]",
          className,
        )}
      >
        No hay datos de tendencia disponibles.
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)}>
      {/* Bars */}
      <div className="flex items-end gap-1.5 h-36 overflow-x-auto pb-1">
        {trend.map((point) => (
          <div
            key={point.period}
            className="flex flex-col items-center gap-1 shrink-0"
            style={{ minWidth: "2.5rem" }}
          >
            {/* NPS score label on top of bar */}
            <span
              className={cn(
                "text-[10px] font-semibold tabular-nums leading-none",
                npsLabelColor(point.nps_score),
              )}
            >
              {point.nps_score > 0 ? "+" : ""}
              {point.nps_score}
            </span>

            {/* Bar */}
            <div className="relative w-full flex items-end" style={{ height: "80px" }}>
              <div
                className={cn(
                  "w-full rounded-t-sm transition-all",
                  npsBarColor(point.nps_score),
                )}
                style={{ height: `${barHeightPct(point.nps_score)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Period labels + response counts */}
      <div className="flex gap-1.5 overflow-x-auto mt-1">
        {trend.map((point) => (
          <div
            key={point.period}
            className="flex flex-col items-center gap-0.5 shrink-0"
            style={{ minWidth: "2.5rem" }}
          >
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] truncate max-w-[2.5rem] text-center">
              {point.period}
            </span>
            <span className="text-[9px] text-[hsl(var(--muted-foreground))] tabular-nums">
              {point.responses}R
            </span>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-sm bg-green-500" />
          <span className="text-xs text-[hsl(var(--muted-foreground))]">NPS &gt; 30</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-sm bg-yellow-400" />
          <span className="text-xs text-[hsl(var(--muted-foreground))]">NPS 0–30</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-sm bg-red-500" />
          <span className="text-xs text-[hsl(var(--muted-foreground))]">NPS &lt; 0</span>
        </div>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          R = respuestas
        </span>
      </div>
    </div>
  );
}
