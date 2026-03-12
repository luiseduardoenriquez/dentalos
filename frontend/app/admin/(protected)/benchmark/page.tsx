"use client";

/**
 * SA-U03 Tenant Comparison (Benchmark) page.
 *
 * Allows a superadmin to compare 2–5 clinics side-by-side across key
 * operational metrics.  Each tenant becomes a column; metrics are rows.
 * A "plan averages" reference column is appended on the right so the
 * admin can immediately see how each clinic compares against its peers.
 *
 * Color coding per cell:
 *   - MRR and features_used: higher is always better → above avg = green
 *   - For all other metrics: higher is also better (more activity) → above avg = green
 *   - below average = red / neutral = gray
 */

import React from "react";
import {
  useTenantComparison,
  type TenantBenchmarkItem,
  type TenantComparisonResponse,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(cents: number): string {
  return (cents / 100).toLocaleString("es-CO", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function formatNumber(value: number): string {
  return value.toLocaleString("es-CO");
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface MetricRow {
  key: keyof TenantBenchmarkItem;
  label: string;
  format: (value: number) => string;
}

const METRIC_ROWS: MetricRow[] = [
  { key: "patients",          label: "Pacientes",          format: formatNumber },
  { key: "active_users",      label: "Usuarios Activos",   format: formatNumber },
  { key: "appointments_30d",  label: "Citas (30d)",        format: formatNumber },
  { key: "invoices_30d",      label: "Facturas (30d)",     format: formatNumber },
  { key: "mrr_cents",         label: "MRR",                format: formatCurrency },
  { key: "features_used",     label: "Features Usados",    format: formatNumber },
];

// ─── Cell color coding ────────────────────────────────────────────────────────

function cellColorClass(value: number, average: number): string {
  if (average === 0) return "text-[hsl(var(--foreground))]";
  const ratio = value / average;
  if (ratio >= 1.1)
    return "text-green-700 dark:text-green-400 font-semibold";
  if (ratio <= 0.9)
    return "text-red-700 dark:text-red-400 font-semibold";
  return "text-[hsl(var(--foreground))]";
}

function cellBgClass(value: number, average: number): string {
  if (average === 0) return "";
  const ratio = value / average;
  if (ratio >= 1.1)
    return "bg-green-50 dark:bg-green-900/20";
  if (ratio <= 0.9)
    return "bg-red-50 dark:bg-red-900/20";
  return "";
}

// ─── Plan Badge ───────────────────────────────────────────────────────────────

const PLAN_STYLES: Record<string, string> = {
  free:       "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  starter:    "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
  pro:        "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  clinica:    "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300",
  enterprise: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
};

function PlanBadge({ plan }: { plan: string }) {
  const cls = PLAN_STYLES[plan.toLowerCase()] ?? PLAN_STYLES.free;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        cls,
      )}
    >
      {plan}
    </span>
  );
}

// ─── Comparison Table ─────────────────────────────────────────────────────────

interface ComparisonTableProps {
  data: TenantComparisonResponse;
}

function ComparisonTable({ data }: ComparisonTableProps) {
  const { tenants, plan_averages } = data;

  if (tenants.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            No se encontraron clinicas con los IDs proporcionados.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Resultados de comparacion
        </CardTitle>
        <CardDescription>
          Verde = por encima del promedio del plan &bull; Rojo = por debajo
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {/* Tenant name row */}
              <tr className="border-b bg-[hsl(var(--muted)/0.4)]">
                <th className="w-44 px-4 py-3 text-left font-medium text-[hsl(var(--muted-foreground))] sticky left-0 bg-[hsl(var(--muted)/0.4)]">
                  Metrica
                </th>
                {tenants.map((t) => (
                  <th
                    key={t.tenant_id}
                    className="px-4 py-3 text-center font-medium min-w-[160px]"
                  >
                    <div className="flex flex-col items-center gap-1">
                      <span className="leading-tight truncate max-w-[140px]" title={t.tenant_name}>
                        {t.tenant_name}
                      </span>
                      <PlanBadge plan={t.plan_name} />
                    </div>
                  </th>
                ))}
                {/* Plan averages reference column */}
                <th className="px-4 py-3 text-center font-medium min-w-[140px] border-l-2 border-indigo-200 dark:border-indigo-700 bg-indigo-50/60 dark:bg-indigo-900/20">
                  <div className="flex flex-col items-center gap-1">
                    <span className="text-indigo-700 dark:text-indigo-300">
                      Promedio del Plan
                    </span>
                    <span className="text-xs font-normal text-indigo-500 dark:text-indigo-400">
                      referencia
                    </span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {METRIC_ROWS.map((row, rowIdx) => {
                const avgKey = row.key as string;
                const planAvgValue: number =
                  typeof plan_averages[avgKey] === "number"
                    ? (plan_averages[avgKey] as number)
                    : 0;

                return (
                  <tr
                    key={row.key}
                    className={cn(
                      "border-b last:border-0",
                      rowIdx % 2 === 0
                        ? "bg-[hsl(var(--background))]"
                        : "bg-[hsl(var(--muted)/0.15)]",
                    )}
                  >
                    {/* Metric label */}
                    <td className="px-4 py-3 font-medium text-[hsl(var(--foreground))] sticky left-0 bg-inherit whitespace-nowrap">
                      {row.label}
                    </td>

                    {/* Tenant values */}
                    {tenants.map((t) => {
                      const raw = t[row.key];
                      const value = typeof raw === "number" ? raw : 0;
                      const colorCls = cellColorClass(value, planAvgValue);
                      const bgCls = cellBgClass(value, planAvgValue);
                      return (
                        <td
                          key={t.tenant_id}
                          className={cn(
                            "px-4 py-3 text-center tabular-nums transition-colors",
                            bgCls,
                            colorCls,
                          )}
                        >
                          {row.format(value)}
                        </td>
                      );
                    })}

                    {/* Plan average reference cell */}
                    <td className="px-4 py-3 text-center tabular-nums border-l-2 border-indigo-200 dark:border-indigo-700 bg-indigo-50/60 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 font-medium">
                      {planAvgValue > 0 ? row.format(planAvgValue) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function ComparisonLoadingSkeleton({ count }: { count: number }) {
  const cols = Math.max(count, 2);
  return (
    <Card>
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-52" />
        <Skeleton className="h-3 w-72 mt-1" />
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-[hsl(var(--muted)/0.4)]">
                <th className="w-44 px-4 py-3">
                  <Skeleton className="h-4 w-20" />
                </th>
                {Array.from({ length: cols }).map((_, i) => (
                  <th key={i} className="px-4 py-3 min-w-[160px]">
                    <div className="flex flex-col items-center gap-1">
                      <Skeleton className="h-4 w-28" />
                      <Skeleton className="h-3 w-16 rounded-full" />
                    </div>
                  </th>
                ))}
                <th className="px-4 py-3 min-w-[140px] border-l-2 border-indigo-200 dark:border-indigo-700">
                  <Skeleton className="h-4 w-24 mx-auto" />
                </th>
              </tr>
            </thead>
            <tbody>
              {METRIC_ROWS.map((row) => (
                <tr key={row.key} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-28" />
                  </td>
                  {Array.from({ length: cols }).map((_, i) => (
                    <td key={i} className="px-4 py-3 text-center">
                      <Skeleton className="h-4 w-20 mx-auto" />
                    </td>
                  ))}
                  <td className="px-4 py-3 text-center border-l-2 border-indigo-200 dark:border-indigo-700">
                    <Skeleton className="h-4 w-16 mx-auto" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Input Form ────────────────────────────────────────────────────────────────

interface InputFormProps {
  rawInput: string;
  onRawInputChange: (value: string) => void;
  onCompare: () => void;
  validationError: string | null;
  isLoading: boolean;
}

function InputForm({
  rawInput,
  onRawInputChange,
  onCompare,
  validationError,
  isLoading,
}: InputFormProps) {
  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") onCompare();
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Seleccionar clinicas
        </CardTitle>
        <CardDescription>
          Ingresa entre 2 y 5 IDs de clinicas separados por coma.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex flex-col gap-1.5 flex-1">
            <Label htmlFor="tenant-ids-input" className="text-sm font-medium">
              IDs de clinicas
            </Label>
            <Input
              id="tenant-ids-input"
              placeholder="ej: abc123, def456, ghi789"
              value={rawInput}
              onChange={(e) => onRawInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              className={cn(
                "font-mono text-sm",
                validationError
                  ? "border-red-400 focus-visible:ring-red-400"
                  : "",
              )}
              disabled={isLoading}
            />
            {validationError && (
              <p className="text-xs text-red-600 dark:text-red-400">
                {validationError}
              </p>
            )}
          </div>
          <Button
            onClick={onCompare}
            disabled={isLoading || !!validationError || rawInput.trim() === ""}
            className="bg-indigo-600 hover:bg-indigo-700 text-white shrink-0"
          >
            {isLoading ? "Comparando…" : "Comparar"}
          </Button>
        </div>
        <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
          Puedes encontrar el ID de una clinica en la pagina de detalle del tenant.
        </p>
      </CardContent>
    </Card>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function BenchmarkPage() {
  const [rawInput, setRawInput] = React.useState<string>("");
  const [tenantIds, setTenantIds] = React.useState<string[]>([]);
  const [validationError, setValidationError] = React.useState<string | null>(null);

  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useTenantComparison(tenantIds);

  function parseAndValidate(raw: string): string[] | null {
    const parts = raw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    if (parts.length < 2) {
      setValidationError("Debes ingresar al menos 2 IDs de clinicas.");
      return null;
    }
    if (parts.length > 5) {
      setValidationError("Puedes comparar un maximo de 5 clinicas a la vez.");
      return null;
    }

    const unique = Array.from(new Set(parts));
    if (unique.length !== parts.length) {
      setValidationError("Los IDs de clinicas no pueden repetirse.");
      return null;
    }

    setValidationError(null);
    return unique;
  }

  function handleRawInputChange(value: string) {
    setRawInput(value);
    // Clear validation error on edit so the user sees live feedback
    if (validationError) {
      const parts = value
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
      if (parts.length >= 2 && parts.length <= 5) {
        setValidationError(null);
      }
    }
  }

  function handleCompare() {
    const ids = parseAndValidate(rawInput);
    if (ids) {
      setTenantIds(ids);
    }
  }

  const hasQueried = tenantIds.length >= 2;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Comparar Clinicas</h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Compara metricas entre 2 a 5 clinicas y contrasta con el promedio de su plan.
        </p>
      </div>

      {/* Input form */}
      <InputForm
        rawInput={rawInput}
        onRawInputChange={handleRawInputChange}
        onCompare={handleCompare}
        validationError={validationError}
        isLoading={isLoading}
      />

      {/* Legend */}
      {hasQueried && (
        <div className="flex flex-wrap items-center gap-4 text-xs text-[hsl(var(--muted-foreground))]">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm bg-green-100 border border-green-400 dark:bg-green-900/40 dark:border-green-600" />
            Por encima del promedio (&ge;10%)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm bg-red-100 border border-red-400 dark:bg-red-900/40 dark:border-red-600" />
            Por debajo del promedio (&le;10%)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm bg-indigo-50 border border-indigo-300 dark:bg-indigo-900/30 dark:border-indigo-600" />
            Columna de referencia (promedio del plan)
          </span>
        </div>
      )}

      {/* Loading state */}
      {isLoading && hasQueried && (
        <ComparisonLoadingSkeleton count={tenantIds.length} />
      )}

      {/* Error state */}
      {isError && hasQueried && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Error al cargar los datos de comparacion. Verifica que los IDs
              sean validos y que tengas conexion con la API.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="border-indigo-300 text-indigo-700 hover:bg-indigo-50 dark:border-indigo-700 dark:text-indigo-300 dark:hover:bg-indigo-900/30"
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Results table */}
      {!isLoading && !isError && data && hasQueried && (
        <ComparisonTable data={data} />
      )}

      {/* Empty state — before any query */}
      {!hasQueried && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-16 text-center">
            <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
              Ingresa los IDs de las clinicas que deseas comparar
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Los resultados apareceran aqui una vez que hagas clic en "Comparar".
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
