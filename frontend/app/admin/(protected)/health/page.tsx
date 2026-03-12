"use client";

import * as React from "react";
import { useAdminHealth, type SystemHealthResponse } from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Formats an ISO timestamp for display using the user's local timezone.
 */
function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-CO", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

/**
 * Returns Tailwind classes for a latency badge based on ms thresholds.
 * green ≤100ms | amber ≤500ms | red >500ms
 */
function latencyBadgeClasses(ms: number): string {
  if (ms <= 100) {
    return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300";
  }
  if (ms <= 500) {
    return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300";
  }
  return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
}

/**
 * Formats a latency value for display.
 */
function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

// ─── Service Card ──────────────────────────────────────────────────────────────

interface ServiceDetail {
  healthy: boolean;
  latency_ms: number;
  version?: string;
  details?: Record<string, unknown>;
}

interface ServiceCardProps {
  label: string;
  connected: boolean;
  detail?: ServiceDetail;
}

function ServiceCard({ label, connected, detail }: ServiceCardProps) {
  const [expanded, setExpanded] = React.useState(false);
  const hasDetails = detail?.details && Object.keys(detail.details).length > 0;

  return (
    <Card>
      <CardContent className="py-5">
        {/* Main row */}
        <div className="flex items-start gap-4">
          {/* Status dot */}
          <span
            className={cn(
              "mt-0.5 h-4 w-4 rounded-full shrink-0",
              connected ? "bg-green-500" : "bg-red-500",
            )}
            aria-hidden="true"
          />

          {/* Label + version + status */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground">{label}</p>

            {detail?.version && (
              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                v{detail.version}
              </p>
            )}

            <p
              className={cn(
                "text-xs font-medium mt-0.5",
                connected
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400",
              )}
            >
              {connected ? "Conectado" : "Sin conexion"}
            </p>
          </div>

          {/* Right side: latency badge + expand toggle */}
          <div className="flex flex-col items-end gap-2 shrink-0">
            {detail !== undefined && (
              <span
                className={cn(
                  "inline-block rounded-full px-2 py-0.5 text-xs font-medium tabular-nums",
                  latencyBadgeClasses(detail.latency_ms),
                )}
              >
                {formatLatency(detail.latency_ms)}
              </span>
            )}

            {hasDetails && (
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="text-xs text-[hsl(var(--muted-foreground))] hover:text-foreground flex items-center gap-0.5 transition-colors"
                aria-expanded={expanded}
                aria-label={expanded ? "Ocultar detalles" : "Ver detalles"}
              >
                {expanded ? (
                  <>
                    Ocultar <ChevronUp className="h-3 w-3" />
                  </>
                ) : (
                  <>
                    Detalles <ChevronDown className="h-3 w-3" />
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Expandable details panel */}
        {hasDetails && expanded && (
          <div className="mt-3 ml-8 rounded-md border border-border bg-muted/40 px-3 py-2">
            <dl className="space-y-1">
              {Object.entries(detail!.details!).map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4 text-xs">
                  <dt className="text-[hsl(var(--muted-foreground))] shrink-0">{key}</dt>
                  <dd className="font-medium text-foreground text-right break-all">
                    {String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Latency Summary Bar ───────────────────────────────────────────────────────

interface LatencySummaryBarProps {
  serviceDetails: SystemHealthResponse["service_details"];
}

function LatencySummaryBar({ serviceDetails }: LatencySummaryBarProps) {
  const entries = Object.entries(serviceDetails);
  if (entries.length === 0) return null;

  const totalMs = entries.reduce((sum, [, d]) => sum + d.latency_ms, 0);
  const maxMs = Math.max(...entries.map(([, d]) => d.latency_ms));
  const avgMs = Math.round(totalMs / entries.length);

  return (
    <div className="rounded-lg border border-border bg-card px-5 py-4">
      <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
        <h3 className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
          Resumen de latencia
        </h3>
        <div className="flex items-center gap-4 text-xs text-[hsl(var(--muted-foreground))]">
          <span>
            Total:{" "}
            <span className={cn("font-semibold", latencyBadgeClasses(totalMs).split(" ")[1])}>
              {formatLatency(totalMs)}
            </span>
          </span>
          <span>
            Promedio:{" "}
            <span className={cn("font-semibold", latencyBadgeClasses(avgMs).split(" ")[1])}>
              {formatLatency(avgMs)}
            </span>
          </span>
          <span>
            Maximo:{" "}
            <span className={cn("font-semibold", latencyBadgeClasses(maxMs).split(" ")[1])}>
              {formatLatency(maxMs)}
            </span>
          </span>
        </div>
      </div>

      {/* Per-service latency bars */}
      <div className="space-y-2">
        {entries.map(([key, detail]) => {
          const pct = totalMs > 0 ? Math.round((detail.latency_ms / totalMs) * 100) : 0;
          const label = SERVICE_LABEL_MAP[key] ?? key;
          return (
            <div key={key} className="flex items-center gap-3 text-xs">
              <span className="w-28 shrink-0 text-[hsl(var(--muted-foreground))] truncate">
                {label}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    detail.latency_ms <= 100
                      ? "bg-green-500"
                      : detail.latency_ms <= 500
                        ? "bg-amber-500"
                        : "bg-red-500",
                  )}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span
                className={cn(
                  "w-14 shrink-0 text-right font-medium tabular-nums",
                  detail.latency_ms <= 100
                    ? "text-green-600 dark:text-green-400"
                    : detail.latency_ms <= 500
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-red-600 dark:text-red-400",
                )}
              >
                {formatLatency(detail.latency_ms)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Status Banner ─────────────────────────────────────────────────────────────

interface StatusBannerProps {
  health: SystemHealthResponse;
}

function StatusBanner({ health }: StatusBannerProps) {
  const isHealthy = health.status === "healthy";

  return (
    <div
      className={cn(
        "rounded-lg border px-6 py-4",
        isHealthy
          ? "bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-700/40"
          : "bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-700/40",
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "h-3 w-3 rounded-full shrink-0",
              isHealthy ? "bg-green-500" : "bg-amber-500",
            )}
            aria-hidden="true"
          />
          <p
            className={cn(
              "text-sm font-semibold",
              isHealthy
                ? "text-green-800 dark:text-green-200"
                : "text-amber-800 dark:text-amber-200",
            )}
          >
            {isHealthy
              ? "Todos los sistemas operativos"
              : "Sistema degradado — algunos servicios presentan problemas"}
          </p>
        </div>

        <div className="flex items-center gap-6 text-xs text-[hsl(var(--muted-foreground))]">
          <span>
            Ultima verificacion:{" "}
            <span className="font-medium text-foreground">
              {formatTimestamp(health.timestamp)}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function HealthLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {/* Banner skeleton */}
      <Skeleton className="h-16 w-full rounded-lg" />

      {/* Latency summary bar skeleton */}
      <Skeleton className="h-24 w-full rounded-lg" />

      {/* Service cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="flex items-start gap-4 py-5">
              <Skeleton className="mt-0.5 h-4 w-4 rounded-full shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-3 w-20" />
              </div>
              <Skeleton className="h-5 w-14 rounded-full shrink-0" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Service Definitions ───────────────────────────────────────────────────────

type ServiceKey = "postgres" | "redis" | "rabbitmq" | "storage";

const SERVICES: Array<{ key: ServiceKey; label: string; detailKey: string }> = [
  { key: "postgres", label: "PostgreSQL", detailKey: "postgres" },
  { key: "redis", label: "Redis", detailKey: "redis" },
  { key: "rabbitmq", label: "RabbitMQ", detailKey: "rabbitmq" },
  { key: "storage", label: "Almacenamiento", detailKey: "storage" },
];

/**
 * Maps service_details keys to display labels for the latency summary bar.
 */
const SERVICE_LABEL_MAP: Record<string, string> = {
  postgres: "PostgreSQL",
  redis: "Redis",
  rabbitmq: "RabbitMQ",
  storage: "Almacenamiento",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminHealthPage() {
  const {
    data: health,
    isLoading,
    isError,
    refetch,
    isFetching,
    dataUpdatedAt,
  } = useAdminHealth();

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Estado del sistema
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Monitoreo en tiempo real de los servicios de infraestructura.
            Actualizacion automatica cada 30 segundos.
          </p>
        </div>

        {/* Manual refresh button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          aria-label="Verificar estado ahora"
        >
          <RefreshCw
            className={cn("mr-2 h-4 w-4", isFetching && "animate-spin")}
          />
          Verificar ahora
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && <HealthLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar el estado del sistema. Verifica la conexion con la
              API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Health content */}
      {!isLoading && !isError && health && (
        <>
          {/* Status banner */}
          <StatusBanner health={health} />

          {/* Latency summary bar — only when service_details is available */}
          {health.service_details &&
            Object.keys(health.service_details).length > 0 && (
              <LatencySummaryBar serviceDetails={health.service_details} />
            )}

          {/* Service cards grid */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
              Servicios
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {SERVICES.map(({ key, label, detailKey }) => (
                <ServiceCard
                  key={key}
                  label={label}
                  connected={health[key]}
                  detail={health.service_details?.[detailKey]}
                />
              ))}
            </div>
          </div>

          {/* Last updated timestamp (shown only after at least one successful fetch) */}
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
