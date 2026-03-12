"use client";

import { useState } from "react";
import {
  useCohortAnalysis,
  type CohortAnalysisResponse,
  type CohortRow,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const MONTHS_OPTIONS = [6, 12, 18, 24] as const;
type MonthsOption = (typeof MONTHS_OPTIONS)[number];

// ─── Cell color helper ────────────────────────────────────────────────────────

/**
 * Returns a Tailwind background + text class pair based on retention percentage.
 *
 * >80% → green  (retained, healthy)
 * >50% → amber  (moderate churn)
 * <=50% → red   (significant churn)
 */
function retentionCellClasses(pct: number): string {
  if (pct > 80) {
    return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
  }
  if (pct > 50) {
    return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
  }
  return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function CohortLoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Info card skeleton */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-9 w-16" />
            <Skeleton className="mt-2 h-3 w-36" />
          </CardContent>
        </Card>
      </div>

      {/* Heatmap table skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
          <Skeleton className="mt-1 h-3 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="flex gap-1">
                <Skeleton className="h-7 w-20 shrink-0" />
                <Skeleton className="h-7 w-14 shrink-0" />
                {[1, 2, 3, 4, 5, 6, 7, 8].map((j) => (
                  <Skeleton key={j} className="h-7 w-12 shrink-0" />
                ))}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Info Card ────────────────────────────────────────────────────────────────

interface AvgChurnCardProps {
  avg_churn_month: number;
}

function AvgChurnCard({ avg_churn_month }: AvgChurnCardProps) {
  return (
    <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
      <CardHeader className="pb-2">
        <CardDescription>Mes promedio de mayor churn</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold tabular-nums tracking-tight">
          Mes {avg_churn_month}
        </p>
        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
          Mes en el que mas clinicas suelen cancelar
        </p>
      </CardContent>
    </Card>
  );
}

// ─── Heatmap Table ────────────────────────────────────────────────────────────

interface CohortHeatmapProps {
  cohorts: CohortRow[];
  maxColumns: number;
}

function CohortHeatmap({ cohorts, maxColumns }: CohortHeatmapProps) {
  if (cohorts.length === 0) {
    return (
      <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Mapa de calor de retención
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Sin datos de cohortes disponibles.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Column indices 0..maxColumns-1 correspond to retention[0]..retention[maxColumns-1]
  const columnIndices = Array.from({ length: maxColumns }, (_, i) => i);

  return (
    <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Mapa de calor de retención
        </CardTitle>
        <CardDescription>
          Porcentaje de clínicas activas por mes desde el registro.
          Verde &gt;80% · Ámbar &gt;50% · Rojo ≤50%
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-[hsl(var(--muted)/0.4)]">
                {/* Cohort month label column */}
                <th className="whitespace-nowrap px-3 py-2 text-left font-medium text-[hsl(var(--muted-foreground))]">
                  Cohorte
                </th>
                {/* Signup count column */}
                <th className="whitespace-nowrap px-2 py-2 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  Registros
                </th>
                {/* Retention month columns */}
                {columnIndices.map((idx) => (
                  <th
                    key={idx}
                    className="whitespace-nowrap px-2 py-2 text-center font-medium text-[hsl(var(--muted-foreground))]"
                  >
                    Mes {idx}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cohorts.map((row) => (
                <tr
                  key={row.cohort_month}
                  className="border-b last:border-0 hover:bg-[hsl(var(--muted)/0.2)] transition-colors"
                >
                  {/* Cohort month (YYYY-MM) */}
                  <td className="whitespace-nowrap px-3 py-1.5 font-mono font-medium tabular-nums">
                    {row.cohort_month}
                  </td>
                  {/* Signup count */}
                  <td className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums text-[hsl(var(--muted-foreground))]">
                    {row.signup_count.toLocaleString("es-CO")}
                  </td>
                  {/* Retention cells */}
                  {columnIndices.map((idx) => {
                    const pct = row.retention[idx];
                    const hasData = pct !== undefined && pct !== null;

                    return (
                      <td key={idx} className="p-1.5 text-center">
                        {hasData ? (
                          <span
                            className={cn(
                              "inline-block w-full rounded px-1.5 py-0.5 font-semibold tabular-nums",
                              retentionCellClasses(pct),
                            )}
                          >
                            {pct.toFixed(0)}%
                          </span>
                        ) : (
                          <span className="inline-block w-full rounded px-1.5 py-0.5 bg-[hsl(var(--muted)/0.4)] text-[hsl(var(--muted-foreground))]">
                            —
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CohortAnalysisPage() {
  const [selectedMonths, setSelectedMonths] = useState<MonthsOption>(12);

  const { data, isLoading, isError, refetch } =
    useCohortAnalysis(selectedMonths);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Análisis de Cohortes
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Retención mensual por cohorte de registro
        </p>
      </div>

      {/* Months selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
          Periodo:
        </span>
        <div className="flex gap-1.5">
          {MONTHS_OPTIONS.map((months) => (
            <Button
              key={months}
              variant={selectedMonths === months ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedMonths(months)}
              className="h-8 px-3 text-xs"
            >
              {months} meses
            </Button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && <CohortLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar el análisis de cohortes. Verifica la conexión con
              la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Data state */}
      {data && !isLoading && (
        <>
          {/* Info card */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <AvgChurnCard avg_churn_month={data.avg_churn_month} />
          </div>

          {/* Cohort heatmap table */}
          <CohortHeatmap
            cohorts={data.cohorts}
            maxColumns={data.months_tracked}
          />
        </>
      )}
    </div>
  );
}
