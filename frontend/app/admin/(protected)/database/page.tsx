"use client";

import * as React from "react";
import {
  useDatabaseMetrics,
  type DatabaseMetricsResponse,
  type TableSizeItem,
  type SlowQueryItem,
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
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatNumber(value: number): string {
  return value.toLocaleString("es-CO");
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(1)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/**
 * Truncates a SQL query string to a maximum character count for display.
 * Preserves meaningful leading tokens (SELECT, UPDATE, etc.).
 */
function truncateQuery(query: string, maxLength = 90): string {
  const trimmed = query.replace(/\s+/g, " ").trim();
  if (trimmed.length <= maxLength) return trimmed;
  return `${trimmed.slice(0, maxLength)}…`;
}

// ─── Ratio color helpers ───────────────────────────────────────────────────────

/**
 * Returns text color classes for index_hit_ratio and cache_hit_ratio.
 * green if >95, yellow if >90, red otherwise.
 */
function ratioColorClasses(ratio: number): string {
  if (ratio > 95) return "text-green-600 dark:text-green-400";
  if (ratio > 90) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/**
 * Returns a brief hint label below the ratio value.
 */
function ratioHint(ratio: number): string {
  if (ratio > 95) return "Excelente — por encima del 95%";
  if (ratio > 90) return "Aceptable — entre 90% y 95%";
  return "Critico — por debajo del 90%";
}

// ─── KPI Card ──────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: React.ReactNode;
  valueClassName?: string;
}

function KpiCard({ title, value, subtitle, valueClassName }: KpiCardProps) {
  return (
    <Card>
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

// ─── Connection Pool Card ─────────────────────────────────────────────────────

interface ConnectionPoolCardProps {
  active: number;
  idle: number;
  max: number;
}

function ConnectionPoolCard({ active, idle, max }: ConnectionPoolCardProps) {
  const usedPct = max > 0 ? Math.min((active / max) * 100, 100) : 0;
  const isHighLoad = usedPct >= 80;
  const isMediumLoad = usedPct >= 60;

  const barColorClass = isHighLoad
    ? "bg-red-500"
    : isMediumLoad
      ? "bg-amber-500"
      : "bg-green-500";

  const valuColorClass = isHighLoad
    ? "text-red-600 dark:text-red-400"
    : isMediumLoad
      ? "text-amber-600 dark:text-amber-400"
      : "text-green-600 dark:text-green-400";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>Conexiones Activas</CardDescription>
      </CardHeader>
      <CardContent>
        <p
          className={cn(
            "text-3xl font-bold tabular-nums tracking-tight",
            valuColorClass,
          )}
        >
          {formatNumber(active)}
          <span className="text-base font-normal text-[hsl(var(--muted-foreground))]">
            /{formatNumber(max)}
          </span>
        </p>
        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
          {usedPct.toFixed(0)}% del pool utilizado
        </p>
        {/* Progress bar */}
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[hsl(var(--muted))]">
          <div
            className={cn("h-full rounded-full transition-all duration-500", barColorClass)}
            style={{ width: `${usedPct.toFixed(1)}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Largest Tables Section ────────────────────────────────────────────────────

interface LargestTablesSectionProps {
  tables: TableSizeItem[];
}

function LargestTablesSection({ tables }: LargestTablesSectionProps) {
  if (tables.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Tablas mas grandes
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
          Tablas mas grandes
        </CardTitle>
        <CardDescription>
          Ordenadas por tamano total en disco
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-[hsl(var(--muted)/0.4)]">
                <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">
                  Schema
                </th>
                <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">
                  Tabla
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  Tamano
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  Filas
                </th>
              </tr>
            </thead>
            <tbody>
              {tables.map((row, idx) => (
                <tr
                  key={`${row.schema_name}.${row.table_name}.${idx}`}
                  className="border-b last:border-0 hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
                >
                  <td className="px-4 py-2.5 font-mono text-xs text-[hsl(var(--muted-foreground))]">
                    {row.schema_name}
                  </td>
                  <td className="px-4 py-2.5 font-medium">{row.table_name}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {row.total_size}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-[hsl(var(--muted-foreground))]">
                    {formatNumber(row.row_count)}
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

// ─── Slow Queries Section ─────────────────────────────────────────────────────

interface SlowQueriesSectionProps {
  queries: SlowQueryItem[];
}

function SlowQueriesSection({ queries }: SlowQueriesSectionProps) {
  if (queries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Consultas lentas
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            No hay datos de pg_stat_statements disponibles.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Consultas lentas
        </CardTitle>
        <CardDescription>
          Consultas con mayor tiempo promedio de ejecucion
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-[hsl(var(--muted)/0.4)]">
                <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] w-1/2">
                  Query
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  Llamadas
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  Tiempo Promedio
                </th>
                <th className="px-4 py-2.5 text-right font-medium text-[hsl(var(--muted-foreground))]">
                  Tiempo Total
                </th>
              </tr>
            </thead>
            <tbody>
              {queries.map((row, idx) => (
                <tr
                  key={idx}
                  className="border-b last:border-0 hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
                >
                  <td className="px-4 py-2.5 font-mono text-xs max-w-xs">
                    <span
                      title={row.query}
                      className="block truncate"
                    >
                      {truncateQuery(row.query)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-[hsl(var(--muted-foreground))]">
                    {formatNumber(row.calls)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums font-medium">
                    {formatMs(row.mean_time_ms)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-[hsl(var(--muted-foreground))]">
                    {formatMs(row.total_time_ms)}
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

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function DatabaseLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {/* KPI grid skeleton — 7 cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-9 w-24" />
              <Skeleton className="h-3 w-40 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Largest tables skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-44" />
          <Skeleton className="h-3 w-56 mt-1" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Slow queries skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-36" />
          <Skeleton className="h-3 w-64 mt-1" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminDatabasePage() {
  const {
    data: metrics,
    isLoading,
    isError,
    refetch,
    isFetching,
    dataUpdatedAt,
  } = useDatabaseMetrics();

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Base de Datos</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Metricas de rendimiento de PostgreSQL. Actualizacion automatica cada
            60 segundos.
          </p>
        </div>

        {/* Manual refresh */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          aria-label="Actualizar metricas de base de datos ahora"
        >
          <RefreshCw
            className={cn("mr-2 h-4 w-4", isFetching && "animate-spin")}
          />
          Actualizar ahora
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && <DatabaseLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar las metricas de base de datos. Verifica la
              conexion con la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Main content */}
      {!isLoading && !isError && metrics && (
        <>
          {/* KPI grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Tamano Total */}
            <KpiCard
              title="Tamano Total"
              value={metrics.total_db_size}
              subtitle="Tamano total de la base de datos"
            />

            {/* Esquemas (tenant schemas) */}
            <KpiCard
              title="Esquemas"
              value={formatNumber(metrics.schema_count)}
              subtitle="Esquemas activos en PostgreSQL"
            />

            {/* Conexiones Activas — uses custom card with progress bar */}
            <ConnectionPoolCard
              active={metrics.connection_pool_active}
              idle={metrics.connection_pool_idle}
              max={metrics.connection_pool_max}
            />

            {/* Conexiones Idle */}
            <KpiCard
              title="Conexiones Idle"
              value={formatNumber(metrics.connection_pool_idle)}
              subtitle="Conexiones abiertas sin actividad"
            />

            {/* Index Hit Ratio */}
            <KpiCard
              title="Index Hit Ratio"
              value={`${metrics.index_hit_ratio.toFixed(1)}%`}
              subtitle={ratioHint(metrics.index_hit_ratio)}
              valueClassName={ratioColorClasses(metrics.index_hit_ratio)}
            />

            {/* Cache Hit Ratio */}
            <KpiCard
              title="Cache Hit Ratio"
              value={`${metrics.cache_hit_ratio.toFixed(1)}%`}
              subtitle={ratioHint(metrics.cache_hit_ratio)}
              valueClassName={ratioColorClasses(metrics.cache_hit_ratio)}
            />

            {/* Dead Tuples */}
            <KpiCard
              title="Dead Tuples"
              value={formatNumber(metrics.dead_tuples_total)}
              subtitle={
                metrics.dead_tuples_total > 100_000
                  ? "Alto — considera ejecutar VACUUM"
                  : "Dentro del rango aceptable"
              }
              valueClassName={
                metrics.dead_tuples_total > 100_000
                  ? "text-red-600 dark:text-red-400"
                  : undefined
              }
            />
          </div>

          {/* Largest tables */}
          <LargestTablesSection tables={metrics.largest_tables} />

          {/* Slow queries */}
          <SlowQueriesSection queries={metrics.slow_queries} />

          {/* Last updated timestamp */}
          {dataUpdatedAt > 0 && (
            <p className="text-xs text-[hsl(var(--muted-foreground))] text-right">
              Datos actualizados:{" "}
              {new Date(dataUpdatedAt).toLocaleTimeString("es-CO")}
              {isFetching && (
                <span className="ml-2 inline-flex items-center gap-1">
                  <RefreshCw className="h-3 w-3 animate-spin" />
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
