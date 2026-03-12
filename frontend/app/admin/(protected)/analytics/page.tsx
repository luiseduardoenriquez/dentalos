"use client";

import * as React from "react";
import { useAdminAnalytics, type PlatformAnalyticsResponse } from "@/lib/hooks/use-admin";
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

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function formatNumber(value: number): string {
  return value.toLocaleString("es-CO");
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

// ─── Plan color mapping ────────────────────────────────────────────────────────

const PLAN_COLORS: Record<string, string> = {
  free: "bg-slate-400",
  starter: "bg-sky-500",
  pro: "bg-violet-500",
  clinica: "bg-teal-500",
  enterprise: "bg-amber-500",
};

function planBarColor(planName: string): string {
  const key = planName.toLowerCase();
  return PLAN_COLORS[key] ?? "bg-slate-400";
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: React.ReactNode;
  valueClassName?: string;
  className?: string;
}

function KpiCard({ title, value, subtitle, valueClassName, className }: KpiCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
      </CardHeader>
      <CardContent>
        <p
          className={cn(
            "text-3xl font-bold tabular-nums tracking-tight",
            valueClassName,
          )}
        >
          {value}
        </p>
        {subtitle && (
          <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
            {subtitle}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function AnalyticsLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {/* KPI skeletons */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-9 w-28" />
              <Skeleton className="h-3 w-40 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Extra metric card skeletons */}
      <div className="grid gap-4 sm:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-36" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-9 w-24" />
              <Skeleton className="h-3 w-32 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Plan distribution skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex flex-col gap-1">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-4 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Top tenants skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-52" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Churn Rate Card ──────────────────────────────────────────────────────────

interface ChurnRateCardProps {
  churn_rate: number;
}

function ChurnRateCard({ churn_rate }: ChurnRateCardProps) {
  const isLow = churn_rate < 5;
  const isMedium = churn_rate >= 5 && churn_rate <= 10;
  const isHigh = churn_rate > 10;

  return (
    <Card
      className={cn(
        "border",
        isHigh
          ? "border-red-200 bg-red-50/50 dark:border-red-700/40 dark:bg-red-900/10"
          : isMedium
            ? "border-amber-200 bg-amber-50/50 dark:border-amber-700/40 dark:bg-amber-900/10"
            : "border-green-200 bg-green-50/50 dark:border-green-700/40 dark:bg-green-900/10",
      )}
    >
      <CardHeader className="pb-2">
        <CardDescription>Tasa de cancelacion (churn)</CardDescription>
      </CardHeader>
      <CardContent>
        <p
          className={cn(
            "text-3xl font-bold tabular-nums tracking-tight",
            isHigh
              ? "text-red-700 dark:text-red-300"
              : isMedium
                ? "text-amber-700 dark:text-amber-300"
                : "text-green-700 dark:text-green-300",
          )}
        >
          {formatPercent(churn_rate)}
        </p>
        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
          {isLow
            ? "Saludable — por debajo del 5%"
            : isMedium
              ? "Moderado — entre 5% y 10%"
              : "Critico — por encima del 10%"}
        </p>
      </CardContent>
    </Card>
  );
}

// ─── Plan Distribution ────────────────────────────────────────────────────────

interface PlanDistributionProps {
  distribution: { plan_name: string; count: number }[];
}

function PlanDistributionSection({ distribution }: PlanDistributionProps) {
  const total = distribution.reduce((sum, d) => sum + d.count, 0);
  const sorted = [...distribution].sort((a, b) => b.count - a.count);

  if (total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Distribucion por plan
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Sin datos disponibles.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Distribucion por plan
        </CardTitle>
        <CardDescription>
          {formatNumber(total)} clinicas en total
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4">
          {sorted.map((item) => {
            const pct = total > 0 ? (item.count / total) * 100 : 0;
            const barColor = planBarColor(item.plan_name);
            return (
              <div key={item.plan_name} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white",
                        barColor,
                      )}
                    >
                      {item.plan_name}
                    </span>
                    <span className="font-medium tabular-nums">
                      {formatNumber(item.count)} clinicas
                    </span>
                  </div>
                  <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums">
                    {formatPercent(pct)}
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-[hsl(var(--muted))]">
                  <div
                    className={cn("h-2 rounded-full transition-all", barColor)}
                    style={{ width: `${pct.toFixed(1)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Top Tenants Table ─────────────────────────────────────────────────────────

interface TopTenantsProps {
  tenants: {
    tenant_id: string;
    name: string;
    mrr_cents: number;
    patients: number;
  }[];
}

function TopTenantsTable({ tenants }: TopTenantsProps) {
  const sorted = [...tenants]
    .sort((a, b) => b.mrr_cents - a.mrr_cents)
    .slice(0, 10);

  if (sorted.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Top 10 clinicas por MRR
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Sin datos disponibles.
          </p>
        </CardContent>
      </Card>
    );
  }

  const maxMrr = sorted[0].mrr_cents;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Top 10 clinicas por MRR
        </CardTitle>
        <CardDescription>Ordenadas por ingresos recurrentes mensuales</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-[hsl(var(--muted)/0.4)]">
                <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">
                  #
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">
                  Clinica
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  MRR
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  Pacientes
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((tenant, idx) => {
                const barPct =
                  maxMrr > 0 ? (tenant.mrr_cents / maxMrr) * 100 : 0;
                return (
                  <tr
                    key={tenant.tenant_id}
                    className="border-b last:border-0 hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
                  >
                    <td className="px-4 py-2.5 tabular-nums text-[hsl(var(--muted-foreground))]">
                      {idx + 1}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium leading-tight">
                          {tenant.name}
                        </span>
                        {/* Mini MRR bar inside the row */}
                        <div className="h-1 w-full max-w-[120px] overflow-hidden rounded-full bg-[hsl(var(--muted))]">
                          <div
                            className="h-1 rounded-full bg-[hsl(var(--primary))] transition-all"
                            style={{ width: `${barPct.toFixed(1)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums font-medium">
                      {formatUSD(tenant.mrr_cents)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-[hsl(var(--muted-foreground))]">
                      {formatNumber(tenant.patients)}
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

// ─── Country Distribution ─────────────────────────────────────────────────────

interface CountryDistributionProps {
  distribution: { country: string; count: number }[];
}

function CountryDistributionSection({ distribution }: CountryDistributionProps) {
  const total = distribution.reduce((sum, d) => sum + d.count, 0);
  const sorted = [...distribution].sort((a, b) => b.count - a.count);

  if (total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Distribucion por pais
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Sin datos disponibles.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Distribucion por pais
        </CardTitle>
        <CardDescription>
          {sorted.length} {sorted.length === 1 ? "pais" : "paises"} activos
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col divide-y divide-[hsl(var(--border))]">
          {sorted.map((item) => {
            const pct = total > 0 ? (item.count / total) * 100 : 0;
            return (
              <li
                key={item.country}
                className="flex items-center justify-between py-2.5 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold uppercase tracking-widest rounded bg-[hsl(var(--muted))] px-1.5 py-0.5">
                    {item.country}
                  </span>
                  <span className="text-[hsl(var(--muted-foreground))]">
                    {formatNumber(item.count)}{" "}
                    {item.count === 1 ? "clinica" : "clinicas"}
                  </span>
                </div>
                <span className="tabular-nums text-xs font-medium">
                  {formatPercent(pct)}
                </span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminAnalyticsPage() {
  const { data: analytics, isLoading, isError, refetch } = useAdminAnalytics();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Analitica de plataforma
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Metricas globales de uso, ingresos y crecimiento.
          </p>
        </div>
        <AnalyticsLoadingSkeleton />
      </div>
    );
  }

  if (isError || !analytics) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Analitica de plataforma
          </h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar las analiticas. Verifica la conexion con la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const arrCents = analytics.mrr_cents * 12;
  const avgRevenuePerClinic =
    analytics.active_tenants > 0
      ? Math.round(analytics.mrr_cents / analytics.active_tenants)
      : 0;

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Analitica de plataforma
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Metricas globales de uso, ingresos y crecimiento. Datos con un retraso
          maximo de 5 minutos.
        </p>
      </div>

      {/* Main KPI grid — 7 cards (6 original + new_signups_30d) */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          title="Total clinicas"
          value={formatNumber(analytics.total_tenants)}
          subtitle={`${formatNumber(analytics.active_tenants)} activas`}
        />

        <KpiCard
          title="Ingresos mensuales (MRR)"
          value={formatUSD(analytics.mrr_cents)}
          subtitle="Recurrente mensual"
        />

        <KpiCard
          title="Ingresos anuales (ARR)"
          value={formatUSD(arrCents)}
          subtitle="Proyeccion anual"
        />

        <KpiCard
          title="Usuarios totales"
          value={formatNumber(analytics.total_users)}
          subtitle="En toda la plataforma"
        />

        <KpiCard
          title="Total pacientes"
          value={formatNumber(analytics.total_patients)}
          subtitle="En toda la plataforma"
        />

        <KpiCard
          title="Usuarios activos mensuales (MAU)"
          value={formatNumber(analytics.mau)}
          subtitle="Usuarios activos mensuales"
        />

        <KpiCard
          title="Nuevas clinicas (30 dias)"
          value={formatNumber(analytics.new_signups_30d)}
          subtitle="Registros en el ultimo mes"
          valueClassName={
            analytics.new_signups_30d > 0
              ? "text-teal-600 dark:text-teal-400"
              : undefined
          }
        />
      </div>

      {/* Secondary metrics */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Churn rate card with color coding */}
        <ChurnRateCard churn_rate={analytics.churn_rate} />

        {/* Average revenue per clinic */}
        <Card className="border-dashed">
          <CardHeader className="pb-2">
            <CardDescription>Ingresos por clinica (promedio)</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums tracking-tight">
              {analytics.active_tenants > 0 ? formatUSD(avgRevenuePerClinic) : "—"}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              MRR / clinicas activas
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Plan distribution */}
      {analytics.plan_distribution && analytics.plan_distribution.length > 0 && (
        <PlanDistributionSection distribution={analytics.plan_distribution} />
      )}

      {/* Top tenants table + Country distribution side by side on wide screens */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {analytics.top_tenants && analytics.top_tenants.length > 0 && (
            <TopTenantsTable tenants={analytics.top_tenants} />
          )}
        </div>
        <div>
          {analytics.country_distribution &&
            analytics.country_distribution.length > 0 && (
              <CountryDistributionSection
                distribution={analytics.country_distribution}
              />
            )}
        </div>
      </div>
    </div>
  );
}
