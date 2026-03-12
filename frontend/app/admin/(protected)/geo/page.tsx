"use client";

/**
 * Admin geographic expansion intelligence page — SA-G04.
 *
 * Sections:
 * 1. Summary cards: Total Countries, Primary Market, Total MRR.
 * 2. Country table: País, Clínicas, Activas, MRR, Plan Top, Tendencia.
 *    - Signup trend rendered as an inline sparkline (proportional div bars).
 *    - Country flags as emoji (CO, MX, PE, CL, AR, EC).
 *
 * Data source: useGeoIntelligence (GET /admin/analytics/geo).
 * Stale time: 5 minutes (set in hook). Indigo accent. Pure Tailwind — no shadcn.
 */

import React from "react";
import { useGeoIntelligence, type GeoCountryMetrics } from "@/lib/hooks/use-admin";

// ─── Constants ────────────────────────────────────────────────────────────────

const COUNTRY_FLAGS: Record<string, string> = {
  CO: "🇨🇴",
  MX: "🇲🇽",
  PE: "🇵🇪",
  CL: "🇨🇱",
  AR: "🇦🇷",
  EC: "🇪🇨",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Format integer cents to a USD dollar string.
 * Example: 150000 → "$1,500"
 */
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

function countryFlag(code: string): string {
  return COUNTRY_FLAGS[code.toUpperCase()] ?? "🌐";
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function GeoLoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Summary card skeletons */}
      <div className="grid gap-4 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5 animate-pulse"
          >
            <div className="h-3 w-28 rounded bg-[hsl(var(--muted))]" />
            <div className="mt-3 h-8 w-20 rounded bg-[hsl(var(--muted))]" />
            <div className="mt-2 h-3 w-36 rounded bg-[hsl(var(--muted))]" />
          </div>
        ))}
      </div>

      {/* Table skeleton */}
      <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
        <div className="px-5 py-4 border-b border-[hsl(var(--border))]">
          <div className="h-5 w-40 rounded bg-[hsl(var(--muted))] animate-pulse" />
        </div>
        <div className="divide-y divide-[hsl(var(--border))]">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-3 animate-pulse">
              <div className="h-4 w-32 rounded bg-[hsl(var(--muted))]" />
              <div className="h-4 w-12 rounded bg-[hsl(var(--muted))]" />
              <div className="h-4 w-12 rounded bg-[hsl(var(--muted))]" />
              <div className="h-4 w-20 rounded bg-[hsl(var(--muted))]" />
              <div className="h-4 w-16 rounded bg-[hsl(var(--muted))]" />
              <div className="h-4 w-24 rounded bg-[hsl(var(--muted))]" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

interface ErrorStateProps {
  onRetry: () => void;
}

function ErrorState({ onRetry }: ErrorStateProps) {
  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-6 py-14 flex flex-col items-center gap-4 text-center">
      <p className="text-sm font-medium text-[hsl(var(--foreground))]">
        No se pudo cargar la inteligencia geográfica
      </p>
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Verifica la conexión con la API e intenta de nuevo.
      </p>
      <button
        onClick={onRetry}
        className="mt-1 inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 text-sm font-medium text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--muted))]"
      >
        Reintentar
      </button>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-6 py-14 flex flex-col items-center gap-2 text-center">
      <p className="text-sm font-medium text-[hsl(var(--foreground))]">
        Sin datos geográficos disponibles
      </p>
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Aún no hay clínicas registradas en ningún país.
      </p>
    </div>
  );
}

// ─── Summary Cards ────────────────────────────────────────────────────────────

interface SummaryCardsProps {
  totalCountries: number;
  primaryMarket: string;
  totalMrrCents: number;
}

function SummaryCards({ totalCountries, primaryMarket, totalMrrCents }: SummaryCardsProps) {
  const cards = [
    {
      label: "Total países",
      value: formatNumber(totalCountries),
      sub: totalCountries === 1 ? "país activo" : "países activos",
    },
    {
      label: "Mercado principal",
      value: `${countryFlag(primaryMarket)} ${primaryMarket}`,
      sub: "Mayor concentración de clínicas",
    },
    {
      label: "MRR total",
      value: formatUSD(totalMrrCents),
      sub: "Ingresos recurrentes mensuales",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5"
        >
          <p className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            {card.label}
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums tracking-tight text-[hsl(var(--foreground))]">
            {card.value}
          </p>
          <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
            {card.sub}
          </p>
        </div>
      ))}
    </div>
  );
}

// ─── Signup Trend Sparkline ────────────────────────────────────────────────────

/**
 * Renders the last 6 months of signup_trend as a row of proportional vertical bars.
 * The tallest bar fills the full height; others scale down proportionally.
 */
interface SparklineProps {
  trend: { month: string; count: number }[];
}

function SignupSparkline({ trend }: SparklineProps) {
  // Take the most recent 6 data points.
  const points = trend.slice(-6);

  if (points.length === 0) {
    return (
      <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>
    );
  }

  const maxCount = Math.max(...points.map((p) => p.count), 1);

  return (
    <div
      className="flex items-end gap-0.5"
      title={points.map((p) => `${p.month}: ${p.count}`).join(" · ")}
      aria-label="Tendencia de registros"
    >
      {points.map((p) => {
        const heightPct = maxCount > 0 ? Math.round((p.count / maxCount) * 100) : 0;
        // Minimum visible height of 2px even if count is 0.
        return (
          <div
            key={p.month}
            className="w-2 rounded-sm bg-indigo-500 opacity-80 transition-all"
            style={{ height: `${Math.max(2, Math.round((heightPct / 100) * 20))}px` }}
            title={`${p.month}: ${p.count}`}
          />
        );
      })}
    </div>
  );
}

// ─── Plan Badge ───────────────────────────────────────────────────────────────

const PLAN_BADGE_CLASSES: Record<string, string> = {
  free: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  starter: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
  pro: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  clinica: "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300",
  enterprise: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
};

function PlanBadge({ plan }: { plan: string | null }) {
  if (!plan) {
    return <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>;
  }
  const key = plan.toLowerCase();
  const classes =
    PLAN_BADGE_CLASSES[key] ??
    "bg-[hsl(var(--muted))] text-[hsl(var(--foreground))]";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${classes}`}
    >
      {plan}
    </span>
  );
}

// ─── Country Table ────────────────────────────────────────────────────────────

interface CountryTableProps {
  countries: GeoCountryMetrics[];
}

function CountryTable({ countries }: CountryTableProps) {
  const sorted = [...countries].sort(
    (a, b) => b.total_mrr_cents - a.total_mrr_cents
  );

  if (sorted.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
      <div className="px-5 py-4 border-b border-[hsl(var(--border))]">
        <h2 className="text-base font-semibold text-[hsl(var(--foreground))]">
          Métricas por país
        </h2>
        <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
          Ordenado por MRR descendente
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)]">
              <th className="px-5 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                País
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Clínicas
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Activas
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                MRR
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Plan Top
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Tendencia
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((country) => {
              const activePct =
                country.tenant_count > 0
                  ? Math.round(
                      (country.active_tenant_count / country.tenant_count) * 100
                    )
                  : 0;
              const isGoodActivation = activePct >= 70;
              const isMedActivation = activePct >= 40 && activePct < 70;

              return (
                <tr
                  key={country.country_code}
                  className="border-b border-[hsl(var(--border))] last:border-0 transition-colors hover:bg-[hsl(var(--muted)/0.3)]"
                >
                  {/* País */}
                  <td className="px-5 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="text-lg leading-none" aria-hidden="true">
                        {countryFlag(country.country_code)}
                      </span>
                      <div className="flex flex-col">
                        <span className="font-medium text-[hsl(var(--foreground))] leading-tight">
                          {country.country_name}
                        </span>
                        <span className="text-xs text-[hsl(var(--muted-foreground))] font-mono">
                          {country.country_code}
                        </span>
                      </div>
                    </div>
                  </td>

                  {/* Clínicas */}
                  <td className="px-4 py-3 text-right tabular-nums text-[hsl(var(--foreground))]">
                    {formatNumber(country.tenant_count)}
                  </td>

                  {/* Activas */}
                  <td className="px-4 py-3 text-right">
                    <div className="flex flex-col items-end gap-0.5">
                      <span
                        className={`tabular-nums font-medium ${
                          isGoodActivation
                            ? "text-green-700 dark:text-green-400"
                            : isMedActivation
                            ? "text-amber-700 dark:text-amber-400"
                            : "text-red-700 dark:text-red-400"
                        }`}
                      >
                        {formatNumber(country.active_tenant_count)}
                      </span>
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        {activePct}%
                      </span>
                    </div>
                  </td>

                  {/* MRR */}
                  <td className="px-4 py-3 text-right tabular-nums font-semibold text-[hsl(var(--foreground))] whitespace-nowrap">
                    {formatUSD(country.total_mrr_cents)}
                  </td>

                  {/* Plan Top */}
                  <td className="px-4 py-3">
                    <PlanBadge plan={country.top_plan} />
                  </td>

                  {/* Tendencia */}
                  <td className="px-4 py-3">
                    <SignupSparkline trend={country.signup_trend} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function GeoIntelligencePage() {
  const { data, isLoading, isError, refetch } = useGeoIntelligence();

  // Derive total MRR from country list when available.
  const totalMrrCents = React.useMemo(
    () =>
      data?.countries.reduce((sum, c) => sum + c.total_mrr_cents, 0) ?? 0,
    [data]
  );

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[hsl(var(--foreground))]">
          Inteligencia Geográfica
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Expansión y métricas por país. Datos con un retraso máximo de 5 minutos.
        </p>
      </div>

      {/* Loading */}
      {isLoading && <GeoLoadingSkeleton />}

      {/* Error */}
      {isError && !isLoading && <ErrorState onRetry={() => refetch()} />}

      {/* Content */}
      {!isLoading && !isError && data && (
        <>
          {/* Summary cards */}
          <SummaryCards
            totalCountries={data.total_countries}
            primaryMarket={data.primary_market}
            totalMrrCents={totalMrrCents}
          />

          {/* Country table */}
          <CountryTable countries={data.countries} />
        </>
      )}

      {/* Empty state when loaded but no countries returned */}
      {!isLoading && !isError && data && data.countries.length === 0 && (
        <EmptyState />
      )}
    </div>
  );
}
