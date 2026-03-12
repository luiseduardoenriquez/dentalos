"use client";

import React from "react";
import {
  useApiUsageMetrics,
  type ApiEndpointMetric,
  type ApiTenantUsage,
} from "@/lib/hooks/use-admin";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatNumber(value: number): string {
  return value.toLocaleString("es-CO");
}

function formatLatency(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

/** Returns Tailwind color classes for an error rate value. */
function errorRateColor(rate: number): string {
  if (rate < 1) return "text-green-600 dark:text-green-400";
  if (rate < 5) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/** Returns Tailwind color classes for an average latency value (ms). */
function latencyColor(ms: number): string {
  if (ms <= 200) return "text-green-600 dark:text-green-400";
  if (ms <= 800) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/** Returns Tailwind bg classes for a bar fill based on error rate. */
function errorRateBarColor(rate: number): string {
  if (rate < 1) return "bg-green-500";
  if (rate < 5) return "bg-amber-500";
  return "bg-red-500";
}

/** Returns a formatted hour label from an ISO string or "HH:00" string. */
function formatHourLabel(raw: string): string {
  // Accept strings like "2026-03-12T14:00:00Z" or "14:00"
  try {
    const d = new Date(raw);
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", hour12: false });
    }
  } catch {
    // fall through
  }
  // If it already looks like "HH:00", return as-is
  return raw.length <= 6 ? raw : raw.slice(0, 5);
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: string;
  valueClassName?: string;
}

function KpiCard({ title, value, subtitle, valueClassName }: KpiCardProps) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-5 py-4">
      <p className="text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
        {title}
      </p>
      <p
        className={[
          "mt-2 text-3xl font-bold tabular-nums tracking-tight",
          valueClassName ?? "text-[hsl(var(--foreground))]",
        ].join(" ")}
      >
        {value}
      </p>
      {subtitle && (
        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">{subtitle}</p>
      )}
    </div>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Cargando metricas">
      {/* KPI skeletons */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-5 py-4"
          >
            <div className="h-3 w-28 rounded bg-[hsl(var(--muted))] animate-pulse" />
            <div className="mt-3 h-8 w-24 rounded bg-[hsl(var(--muted))] animate-pulse" />
            <div className="mt-2 h-3 w-32 rounded bg-[hsl(var(--muted))] animate-pulse" />
          </div>
        ))}
      </div>

      {/* Bar chart skeleton */}
      <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5">
        <div className="mb-4 h-4 w-40 rounded bg-[hsl(var(--muted))] animate-pulse" />
        <div className="flex items-end gap-1 h-32">
          {Array.from({ length: 24 }).map((_, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-[hsl(var(--muted))] animate-pulse"
              style={{ height: `${20 + Math.random() * 80}%` }}
            />
          ))}
        </div>
      </div>

      {/* Table skeletons */}
      <div className="grid gap-6 lg:grid-cols-2">
        {[1, 2].map((t) => (
          <div
            key={t}
            className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden"
          >
            <div className="border-b border-[hsl(var(--border))] px-5 py-4">
              <div className="h-4 w-44 rounded bg-[hsl(var(--muted))] animate-pulse" />
            </div>
            <div className="divide-y divide-[hsl(var(--border))]">
              {[1, 2, 3, 4, 5].map((r) => (
                <div key={r} className="flex items-center gap-3 px-5 py-3">
                  <div className="h-3 w-8 rounded bg-[hsl(var(--muted))] animate-pulse" />
                  <div className="flex-1 h-3 rounded bg-[hsl(var(--muted))] animate-pulse" />
                  <div className="h-3 w-16 rounded bg-[hsl(var(--muted))] animate-pulse" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Requests by Hour Bar Chart ────────────────────────────────────────────────

interface RequestsByHourChartProps {
  data: { hour: string; count: number }[];
}

function RequestsByHourChart({ data }: RequestsByHourChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5">
        <h2 className="text-sm font-semibold text-[hsl(var(--foreground))]">
          Solicitudes por hora
        </h2>
        <p className="mt-4 text-sm text-[hsl(var(--muted-foreground))]">
          Sin datos disponibles.
        </p>
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5">
      <div className="mb-1 flex items-center justify-between gap-4">
        <h2 className="text-sm font-semibold text-[hsl(var(--foreground))]">
          Solicitudes por hora
        </h2>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          Ultimas {data.length} horas
        </span>
      </div>
      <p className="mb-4 text-xs text-[hsl(var(--muted-foreground))]">
        Maximo: {formatNumber(maxCount)} solicitudes
      </p>

      {/* Bar chart */}
      <div
        className="flex items-end gap-[2px] h-36"
        role="img"
        aria-label="Grafico de barras: solicitudes por hora"
      >
        {data.map((d, idx) => {
          const heightPct = maxCount > 0 ? (d.count / maxCount) * 100 : 0;
          return (
            <div
              key={idx}
              className="group relative flex-1 flex flex-col justify-end"
              title={`${formatHourLabel(d.hour)}: ${formatNumber(d.count)} solicitudes`}
            >
              {/* Tooltip on hover */}
              <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center z-10 pointer-events-none">
                <div className="rounded bg-[hsl(var(--foreground))] px-2 py-1 text-[10px] font-medium text-[hsl(var(--background))] whitespace-nowrap">
                  {formatHourLabel(d.hour)}: {formatNumber(d.count)}
                </div>
                <div className="h-1.5 w-1.5 rotate-45 bg-[hsl(var(--foreground))] -mt-[3px]" />
              </div>

              {/* Bar */}
              <div
                className="w-full rounded-t bg-indigo-500 dark:bg-indigo-400 transition-all duration-300 group-hover:bg-indigo-400 dark:group-hover:bg-indigo-300 min-h-[2px]"
                style={{ height: `${Math.max(heightPct, 2)}%` }}
              />
            </div>
          );
        })}
      </div>

      {/* X-axis labels — show every 4th hour to avoid overlap */}
      <div className="mt-1 flex gap-[2px]">
        {data.map((d, idx) => (
          <div key={idx} className="flex-1 text-center">
            {idx % 4 === 0 ? (
              <span className="text-[9px] text-[hsl(var(--muted-foreground))]">
                {formatHourLabel(d.hour)}
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Top Endpoints Table ───────────────────────────────────────────────────────

interface TopEndpointsTableProps {
  endpoints: ApiEndpointMetric[];
}

function TopEndpointsTable({ endpoints }: TopEndpointsTableProps) {
  const sorted = [...endpoints]
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  if (sorted.length === 0) return null;

  const maxCount = sorted[0].count;

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
      <div className="border-b border-[hsl(var(--border))] px-5 py-4">
        <h2 className="text-sm font-semibold text-[hsl(var(--foreground))]">
          Endpoints con mas trafico
        </h2>
        <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
          Top {sorted.length} endpoints por volumen de solicitudes
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)]">
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] w-8">
                #
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">
                Endpoint
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Solicitudes
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Latencia prom.
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Errores
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((ep, idx) => {
              const barPct = maxCount > 0 ? (ep.count / maxCount) * 100 : 0;
              const errorRate = ep.count > 0 ? (ep.error_count / ep.count) * 100 : 0;
              return (
                <tr
                  key={`${ep.method}-${ep.endpoint}-${idx}`}
                  className="border-b border-[hsl(var(--border))] last:border-0 hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
                >
                  <td className="px-4 py-3 tabular-nums text-[hsl(var(--muted-foreground))] text-xs">
                    {idx + 1}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1 min-w-0">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="inline-block shrink-0 rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
                          {ep.method}
                        </span>
                        <span className="truncate font-mono text-xs text-[hsl(var(--foreground))]">
                          {ep.endpoint}
                        </span>
                      </div>
                      {/* Mini volume bar */}
                      <div className="h-1 w-full max-w-[120px] overflow-hidden rounded-full bg-[hsl(var(--muted))]">
                        <div
                          className="h-1 rounded-full bg-indigo-400 dark:bg-indigo-500 transition-all"
                          style={{ width: `${barPct.toFixed(1)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium text-[hsl(var(--foreground))]">
                    {formatNumber(ep.count)}
                  </td>
                  <td
                    className={[
                      "px-4 py-3 text-right tabular-nums font-medium",
                      latencyColor(ep.avg_latency_ms),
                    ].join(" ")}
                  >
                    {formatLatency(ep.avg_latency_ms)}
                  </td>
                  <td
                    className={[
                      "px-4 py-3 text-right tabular-nums",
                      ep.error_count > 0
                        ? errorRateColor(errorRate)
                        : "text-[hsl(var(--muted-foreground))]",
                    ].join(" ")}
                  >
                    {formatNumber(ep.error_count)}
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

// ─── Top Tenants by API Usage Table ────────────────────────────────────────────

interface TopTenantsByUsageProps {
  tenants: ApiTenantUsage[];
  totalRequests: number;
}

function TopTenantsByUsageTable({ tenants, totalRequests }: TopTenantsByUsageProps) {
  const sorted = [...tenants]
    .sort((a, b) => b.request_count - a.request_count)
    .slice(0, 10);

  if (sorted.length === 0) return null;

  const maxCount = sorted[0].request_count;

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
      <div className="border-b border-[hsl(var(--border))] px-5 py-4">
        <h2 className="text-sm font-semibold text-[hsl(var(--foreground))]">
          Clinicas con mas consumo de API
        </h2>
        <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
          Top {sorted.length} clinicas por solicitudes (24h)
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)]">
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] w-8">
                #
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">
                Clinica
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Solicitudes
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                % del total
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((tenant, idx) => {
              const barPct = maxCount > 0 ? (tenant.request_count / maxCount) * 100 : 0;
              const pctOfTotal =
                totalRequests > 0
                  ? (tenant.request_count / totalRequests) * 100
                  : 0;
              return (
                <tr
                  key={tenant.tenant_id}
                  className="border-b border-[hsl(var(--border))] last:border-0 hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
                >
                  <td className="px-4 py-3 tabular-nums text-[hsl(var(--muted-foreground))] text-xs">
                    {idx + 1}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-[hsl(var(--foreground))] leading-tight">
                        {tenant.tenant_name}
                      </span>
                      {/* Mini volume bar */}
                      <div className="h-1 w-full max-w-[120px] overflow-hidden rounded-full bg-[hsl(var(--muted))]">
                        <div
                          className="h-1 rounded-full bg-indigo-400 dark:bg-indigo-500 transition-all"
                          style={{ width: `${barPct.toFixed(1)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium text-[hsl(var(--foreground))]">
                    {formatNumber(tenant.request_count)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-[hsl(var(--muted-foreground))]">
                    {formatPercent(pctOfTotal)}
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

// ─── Error Rate Banner ─────────────────────────────────────────────────────────

interface ErrorRateBannerProps {
  errorRate: number;
}

function ErrorRateBanner({ errorRate }: ErrorRateBannerProps) {
  const isOk = errorRate < 1;
  const isWarn = errorRate >= 1 && errorRate < 5;

  const bannerClass = isOk
    ? "bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-700/40"
    : isWarn
      ? "bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-700/40"
      : "bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-700/40";

  const dotClass = isOk
    ? "bg-green-500"
    : isWarn
      ? "bg-amber-500"
      : "bg-red-500";

  const textClass = isOk
    ? "text-green-800 dark:text-green-200"
    : isWarn
      ? "text-amber-800 dark:text-amber-200"
      : "text-red-800 dark:text-red-200";

  const label = isOk
    ? "Tasa de error saludable — por debajo del 1%"
    : isWarn
      ? "Tasa de error moderada — entre 1% y 5%"
      : "Tasa de error critica — por encima del 5%";

  return (
    <div
      className={["rounded-lg border px-5 py-3 flex items-center gap-3", bannerClass].join(" ")}
      role="status"
      aria-live="polite"
    >
      <span className={["h-2.5 w-2.5 shrink-0 rounded-full", dotClass].join(" ")} aria-hidden="true" />
      <p className={["text-sm font-medium", textClass].join(" ")}>
        {label}
      </p>
      <span className={["ml-auto text-sm font-bold tabular-nums", textClass].join(" ")}>
        {formatPercent(errorRate)}
      </span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ApiMetricsPage() {
  const { data, isLoading, isError, refetch, isFetching, dataUpdatedAt } =
    useApiUsageMetrics();

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[hsl(var(--foreground))]">
            Metricas API
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Uso y rendimiento de la API en las ultimas 24 horas. Actualizacion
            automatica cada 60 segundos.
          </p>
        </div>

        {/* Manual refresh button */}
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          aria-label="Actualizar metricas ahora"
          className="inline-flex items-center gap-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-1.5 text-sm font-medium text-[hsl(var(--foreground))] shadow-sm transition-colors hover:bg-[hsl(var(--muted))] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className={["h-4 w-4", isFetching ? "animate-spin" : ""].join(" ")}
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
              clipRule="evenodd"
            />
          </svg>
          Actualizar
        </button>
      </div>

      {/* Loading state */}
      {isLoading && <LoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-6 py-12 flex flex-col items-center gap-3 text-center">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Error al cargar las metricas de API. Verifica la conexion con el
            servidor.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-1.5 text-sm font-medium transition-colors hover:bg-[hsl(var(--muted))]"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Main content — only when data is available */}
      {!isLoading && !isError && data && (
        <>
          {/* Error rate status banner */}
          <ErrorRateBanner errorRate={data.error_rate_percent} />

          {/* KPI cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              title="Solicitudes totales (24h)"
              value={formatNumber(data.total_requests_24h)}
              subtitle="Todas las rutas de la API"
            />

            <KpiCard
              title="Tasa de error"
              value={formatPercent(data.error_rate_percent)}
              subtitle={
                data.error_rate_percent < 1
                  ? "Dentro del umbral aceptable"
                  : "Por encima del umbral"
              }
              valueClassName={errorRateColor(data.error_rate_percent)}
            />

            <KpiCard
              title="Latencia promedio"
              value={formatLatency(data.avg_latency_ms)}
              subtitle="Tiempo de respuesta medio"
              valueClassName={latencyColor(data.avg_latency_ms)}
            />

            <KpiCard
              title="Latencia P95"
              value={formatLatency(data.p95_latency_ms)}
              subtitle="Percentil 95 de latencia"
              valueClassName={latencyColor(data.p95_latency_ms)}
            />
          </div>

          {/* Requests by hour bar chart */}
          {data.requests_by_hour && data.requests_by_hour.length > 0 && (
            <RequestsByHourChart data={data.requests_by_hour} />
          )}

          {/* Top endpoints + top tenants side by side on large screens */}
          {(data.top_endpoints?.length > 0 || data.top_tenants?.length > 0) && (
            <div className="grid gap-6 lg:grid-cols-2">
              {data.top_endpoints && data.top_endpoints.length > 0 && (
                <TopEndpointsTable endpoints={data.top_endpoints} />
              )}
              {data.top_tenants && data.top_tenants.length > 0 && (
                <TopTenantsByUsageTable
                  tenants={data.top_tenants}
                  totalRequests={data.total_requests_24h}
                />
              )}
            </div>
          )}

          {/* Last updated timestamp */}
          {dataUpdatedAt > 0 && (
            <p className="text-right text-xs text-[hsl(var(--muted-foreground))]">
              Datos actualizados:{" "}
              <span className="font-medium">
                {new Date(dataUpdatedAt).toLocaleTimeString("es-CO")}
              </span>
              {isFetching && (
                <span className="ml-2 inline-flex items-center gap-1">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-3 w-3 animate-spin"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Actualizando...
                </span>
              )}
            </p>
          )}
        </>
      )}
    </div>
  );
}
