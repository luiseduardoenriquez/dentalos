"use client";

/**
 * Admin tenant health page — SA-U02.
 *
 * Displays per-clinic usage metrics and a composite health score so the
 * superadmin can quickly identify clinics that are at risk of churning.
 *
 * Sections:
 * 1. Three KPI cards: Saludables / En Riesgo / Critico counts.
 * 2. Full-width tenant table with usage columns and a scored progress bar.
 *
 * Data source: useTenantHealth → GET /admin/analytics/tenant-health
 *
 * Sort order: pre-sorted by health_score ascending (worst first) so the
 * most critical clinics are always visible at the top without interaction.
 *
 * Health score color thresholds:
 *   >50 → green  |  >20 → amber  |  ≤20 → red
 */

import { useTenantHealth, type TenantHealthListResponse, type TenantUsageMetrics } from "@/lib/hooks/use-admin";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─── Helpers ───────────────────────────────────────────────────────────────────

function formatNumber(value: number): string {
  return value.toLocaleString("es-CO");
}

/**
 * Derive color classes for a health score.
 *   >50 → green  |  >20 → amber  |  ≤20 → red
 */
function scoreColorClasses(score: number): {
  text: string;
  bar: string;
  badge: string;
} {
  if (score > 50) {
    return {
      text: "text-green-700 dark:text-green-400",
      bar: "bg-green-500 dark:bg-green-400",
      badge:
        "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/40",
    };
  }
  if (score > 20) {
    return {
      text: "text-amber-700 dark:text-amber-400",
      bar: "bg-amber-500 dark:bg-amber-400",
      badge:
        "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700/40",
    };
  }
  return {
    text: "text-red-700 dark:text-red-400",
    bar: "bg-red-500 dark:bg-red-400",
    badge:
      "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/40",
  };
}

// ─── KPI Card ──────────────────────────────────────────────────────────────────

interface HealthKpiCardProps {
  title: string;
  count: number;
  /** Tailwind color applied to the count value. */
  valueColorClass: string;
  /** Tailwind color applied to the left accent bar. */
  accentColorClass: string;
  isLoading: boolean;
}

function HealthKpiCard({
  title,
  count,
  valueColorClass,
  accentColorClass,
  isLoading,
}: HealthKpiCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5",
        "flex items-stretch gap-4 overflow-hidden",
      )}
    >
      {/* Colored left accent bar */}
      <div
        className={cn("w-1 shrink-0 rounded-full", accentColorClass)}
        aria-hidden="true"
      />

      <div className="flex flex-col gap-1 min-w-0">
        <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
          {title}
        </p>
        {isLoading ? (
          <Skeleton className="h-9 w-16 mt-1" />
        ) : (
          <p
            className={cn(
              "text-3xl font-bold tabular-nums tracking-tight",
              valueColorClass,
            )}
          >
            {formatNumber(count)}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── KPI Grid ──────────────────────────────────────────────────────────────────

function HealthKpiGrid({
  data,
  isLoading,
}: {
  data: TenantHealthListResponse | undefined;
  isLoading: boolean;
}) {
  return (
    <section aria-label="Indicadores de salud por clinica">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <HealthKpiCard
          title="Saludables"
          count={data?.healthy_count ?? 0}
          valueColorClass="text-green-700 dark:text-green-400"
          accentColorClass="bg-green-500"
          isLoading={isLoading}
        />
        <HealthKpiCard
          title="En Riesgo"
          count={data?.at_risk_count ?? 0}
          valueColorClass="text-amber-700 dark:text-amber-400"
          accentColorClass="bg-amber-500"
          isLoading={isLoading}
        />
        <HealthKpiCard
          title="Critico"
          count={data?.critical_count ?? 0}
          valueColorClass="text-red-700 dark:text-red-400"
          accentColorClass="bg-red-500"
          isLoading={isLoading}
        />
      </div>
    </section>
  );
}

// ─── Risk Level Badge ──────────────────────────────────────────────────────────

/**
 * Badge for the risk_level field.
 *   healthy  → green  "Saludable"
 *   at_risk  → amber  "En riesgo"
 *   critical → red    "Critico"
 */
function RiskLevelBadge({ riskLevel }: { riskLevel: string }) {
  const config: Record<string, { label: string; className: string }> = {
    healthy: {
      label: "Saludable",
      className:
        "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/40",
    },
    at_risk: {
      label: "En riesgo",
      className:
        "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700/40",
    },
    critical: {
      label: "Critico",
      className:
        "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/40",
    },
  };

  const { label, className } = config[riskLevel] ?? config.at_risk;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border whitespace-nowrap",
        className,
      )}
    >
      {label}
    </span>
  );
}

// ─── Score Cell ────────────────────────────────────────────────────────────────

/**
 * Renders the health_score as a numeric value plus a progress bar.
 * Score range: 0–100. Color thresholds: >50 green | >20 amber | ≤20 red.
 */
function ScoreCell({ score }: { score: number }) {
  const colors = scoreColorClasses(score);
  const clampedPct = Math.min(100, Math.max(0, score));

  return (
    <div className="flex flex-col gap-1 min-w-[72px]">
      <span className={cn("font-semibold tabular-nums text-sm", colors.text)}>
        {score}
      </span>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[hsl(var(--muted))]">
        <div
          className={cn("h-1.5 rounded-full transition-all", colors.bar)}
          style={{ width: `${clampedPct}%` }}
        />
      </div>
    </div>
  );
}

// ─── Table Skeleton ────────────────────────────────────────────────────────────

function TableLoadingSkeleton() {
  return (
    <tbody className="divide-y divide-[hsl(var(--border))]">
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i}>
          {/* Clinica */}
          <td className="px-5 py-3">
            <div className="flex flex-col gap-1">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-3 w-20" />
            </div>
          </td>
          {/* Plan */}
          <td className="px-5 py-3">
            <Skeleton className="h-5 w-16 rounded-full" />
          </td>
          {/* Usuarios Activos */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-8" />
          </td>
          {/* Pacientes */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-10" />
          </td>
          {/* Citas */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-10" />
          </td>
          {/* Facturas */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-8" />
          </td>
          {/* Registros */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-10" />
          </td>
          {/* Puntaje */}
          <td className="px-5 py-3">
            <div className="flex flex-col gap-1">
              <Skeleton className="h-4 w-8" />
              <Skeleton className="h-1.5 w-full rounded-full" />
            </div>
          </td>
          {/* Estado */}
          <td className="px-5 py-3">
            <Skeleton className="h-5 w-20 rounded-full" />
          </td>
        </tr>
      ))}
    </tbody>
  );
}

// ─── Tenant Health Table ───────────────────────────────────────────────────────

function TenantHealthTable({
  tenants,
  isLoading,
}: {
  tenants: TenantUsageMetrics[];
  isLoading: boolean;
}) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
      {/* Card header */}
      <div className="px-5 py-4 border-b border-[hsl(var(--border))]">
        <h2 className="text-base font-semibold text-[hsl(var(--card-foreground))]">
          Metricas por clinica
        </h2>
        <p className="mt-0.5 text-sm text-[hsl(var(--muted-foreground))]">
          Ordenadas por puntaje ascendente — las clinicas en peor estado aparecen
          primero
        </p>
      </div>

      <div className="overflow-x-auto">
        <table
          className="w-full text-sm"
          aria-label="Metricas de uso y salud por clinica"
        >
          <thead>
            <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)]">
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Clinica
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Plan
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Usuarios Activos (7d)
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Pacientes (30d)
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Citas (30d)
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Facturas (30d)
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Registros (30d)
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Puntaje
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Estado
              </th>
            </tr>
          </thead>

          {isLoading ? (
            <TableLoadingSkeleton />
          ) : (
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {tenants.length === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                    className="px-5 py-10 text-center text-sm text-[hsl(var(--muted-foreground))]"
                  >
                    No hay clinicas registradas.
                  </td>
                </tr>
              ) : (
                tenants.map((tenant) => (
                  <tr
                    key={tenant.tenant_id}
                    className="hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
                  >
                    {/* Clinica name */}
                    <td className="px-5 py-3 whitespace-nowrap">
                      <span className="font-medium text-[hsl(var(--card-foreground))]">
                        {tenant.tenant_name}
                      </span>
                    </td>

                    {/* Plan badge */}
                    <td className="px-5 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border border-[hsl(var(--border))] bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]">
                        {tenant.plan_name}
                      </span>
                    </td>

                    {/* Active users 7d */}
                    <td className="px-5 py-3 text-right tabular-nums text-[hsl(var(--card-foreground))]">
                      {formatNumber(tenant.active_users_7d)}
                    </td>

                    {/* Patients created 30d */}
                    <td className="px-5 py-3 text-right tabular-nums text-[hsl(var(--card-foreground))]">
                      {formatNumber(tenant.patients_created_30d)}
                    </td>

                    {/* Appointments 30d */}
                    <td className="px-5 py-3 text-right tabular-nums text-[hsl(var(--card-foreground))]">
                      {formatNumber(tenant.appointments_30d)}
                    </td>

                    {/* Invoices 30d */}
                    <td className="px-5 py-3 text-right tabular-nums text-[hsl(var(--card-foreground))]">
                      {formatNumber(tenant.invoices_30d)}
                    </td>

                    {/* Clinical records 30d */}
                    <td className="px-5 py-3 text-right tabular-nums text-[hsl(var(--card-foreground))]">
                      {formatNumber(tenant.clinical_records_30d)}
                    </td>

                    {/* Health score + progress bar */}
                    <td className="px-5 py-3 min-w-[100px]">
                      <ScoreCell score={tenant.health_score} />
                    </td>

                    {/* Risk level badge */}
                    <td className="px-5 py-3 whitespace-nowrap">
                      <RiskLevelBadge riskLevel={tenant.risk_level} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          )}
        </table>
      </div>
    </div>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

/**
 * Tenant health analytics page for superadmin.
 *
 * Data source: useTenantHealth → GET /admin/analytics/tenant-health (stale 10 min).
 *
 * Layout:
 * 1. Page header with title + description.
 * 2. 3-column KPI cards (Saludables, En Riesgo, Critico).
 * 3. Full-width tenant table (worst-first ordering).
 *
 * Error handling: dedicated error card with retry action.
 */
export default function TenantHealthPage() {
  const { data, isLoading, isError, refetch } = useTenantHealth();

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">
          Salud de Clinicas
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Metricas de uso por clinica y puntaje de salud
        </p>
      </div>

      {/* ── Error state ── */}
      {isError && (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6">
          <p className="text-sm text-red-600 dark:text-red-400">
            No se pudo cargar las metricas de salud. Verifica la conexion con la
            API.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => refetch()}
          >
            Reintentar
          </Button>
        </div>
      )}

      {/* ── KPI cards ── */}
      {!isError && <HealthKpiGrid data={data} isLoading={isLoading} />}

      {/* ── Tenant health table ── */}
      {!isError && (
        <TenantHealthTable
          tenants={data?.items ?? []}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}
