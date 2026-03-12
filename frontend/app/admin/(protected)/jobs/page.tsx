"use client";

import * as React from "react";
import {
  useAdminJobs,
  type QueueStatItem,
  type JobMonitorResponse,
} from "@/lib/hooks/use-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  RefreshCw,
  Layers,
  Users,
  InboxIcon,
  Wifi,
  WifiOff,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Maps canonical RabbitMQ queue names to human-readable Spanish labels.
 */
const QUEUE_LABEL_MAP: Record<string, string> = {
  notifications: "Notificaciones",
  clinical: "Clinico",
  compliance: "Cumplimiento",
  voice: "Voz",
  import: "Importacion",
  maintenance: "Mantenimiento",
};

/**
 * Returns the display label for a queue. Falls back to the raw name if not mapped.
 */
function queueLabel(name: string): string {
  return QUEUE_LABEL_MAP[name] ?? name;
}

/**
 * Returns Tailwind classes for messages_ready count based on thresholds.
 * green  = 0     (idle)
 * amber  = 1-99  (processing)
 * red    = ≥100  (backlog)
 */
function messagesReadyColorClasses(count: number): string {
  if (count === 0) {
    return "text-green-600 dark:text-green-400";
  }
  if (count < 100) {
    return "text-amber-600 dark:text-amber-400";
  }
  return "text-red-600 dark:text-red-400";
}

// ─── Queue Card ───────────────────────────────────────────────────────────────

interface QueueCardProps {
  queue: QueueStatItem;
}

function QueueCard({ queue }: QueueCardProps) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base font-semibold truncate">
            {queueLabel(queue.name)}
          </CardTitle>
          <Badge
            variant={queue.connected ? "default" : "destructive"}
            className={cn(
              "shrink-0 text-xs px-2 py-0.5",
              queue.connected
                ? "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/40"
                : "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/40",
            )}
          >
            {queue.connected ? "Conectada" : "Desconectada"}
          </Badge>
        </div>
        <p className="text-xs text-[hsl(var(--muted-foreground))] font-mono">
          {queue.name}
        </p>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 pt-0">
        {/* Messages ready — primary metric, large display */}
        <div className="rounded-lg bg-muted/50 px-4 py-3 text-center">
          <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1 flex items-center justify-center gap-1">
            <InboxIcon className="h-3 w-3" />
            Mensajes en espera
          </p>
          <p
            className={cn(
              "text-3xl font-bold tabular-nums",
              messagesReadyColorClasses(queue.messages_ready),
            )}
          >
            {queue.messages_ready.toLocaleString("es-CO")}
          </p>
        </div>

        {/* Consumer count */}
        <div className="flex items-center justify-between gap-2 text-sm">
          <span className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))]">
            <Users className="h-4 w-4 shrink-0" />
            Consumidores activos
          </span>
          <span
            className={cn(
              "font-semibold tabular-nums",
              queue.consumers > 0
                ? "text-indigo-600 dark:text-indigo-400"
                : "text-[hsl(var(--muted-foreground))]",
            )}
          >
            {queue.consumers}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Connection Banner ─────────────────────────────────────────────────────────

interface ConnectionBannerProps {
  data: JobMonitorResponse;
}

function ConnectionBanner({ data }: ConnectionBannerProps) {
  return (
    <div
      className={cn(
        "rounded-lg border px-6 py-4",
        data.connected
          ? "bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-700/40"
          : "bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-700/40",
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center justify-between gap-4 flex-wrap">
        {/* Left: status dot + message */}
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "h-3 w-3 rounded-full shrink-0 animate-pulse",
              data.connected ? "bg-green-500" : "bg-red-500",
            )}
            aria-hidden="true"
          />
          <p
            className={cn(
              "text-sm font-semibold",
              data.connected
                ? "text-green-800 dark:text-green-200"
                : "text-red-800 dark:text-red-200",
            )}
          >
            {data.connected
              ? "RabbitMQ conectado — broker operativo"
              : "RabbitMQ desconectado — broker no disponible"}
          </p>
        </div>

        {/* Right: exchange name */}
        <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
          <Layers className="h-3.5 w-3.5 shrink-0" />
          <span>
            Exchange:{" "}
            <span className="font-semibold text-foreground font-mono">
              {data.exchange}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Summary Stats Bar ────────────────────────────────────────────────────────

interface SummaryStatsBarProps {
  queues: QueueStatItem[];
}

function SummaryStatsBar({ queues }: SummaryStatsBarProps) {
  const totalMessages = queues.reduce((sum, q) => sum + q.messages_ready, 0);
  const totalConsumers = queues.reduce((sum, q) => sum + q.consumers, 0);
  const connectedCount = queues.filter((q) => q.connected).length;
  const totalQueues = queues.length;

  return (
    <div className="rounded-lg border border-border bg-card px-5 py-4">
      <h3 className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mb-3">
        Resumen global
      </h3>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {/* Queues connected */}
        <div className="flex flex-col gap-1">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Colas conectadas
          </p>
          <p
            className={cn(
              "text-xl font-bold tabular-nums",
              connectedCount === totalQueues
                ? "text-green-600 dark:text-green-400"
                : connectedCount === 0
                  ? "text-red-600 dark:text-red-400"
                  : "text-amber-600 dark:text-amber-400",
            )}
          >
            {connectedCount}
            <span className="text-sm font-normal text-[hsl(var(--muted-foreground))]">
              /{totalQueues}
            </span>
          </p>
        </div>

        {/* Total messages ready */}
        <div className="flex flex-col gap-1">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Mensajes en espera
          </p>
          <p
            className={cn(
              "text-xl font-bold tabular-nums",
              messagesReadyColorClasses(totalMessages),
            )}
          >
            {totalMessages.toLocaleString("es-CO")}
          </p>
        </div>

        {/* Total consumers */}
        <div className="flex flex-col gap-1">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Consumidores totales
          </p>
          <p
            className={cn(
              "text-xl font-bold tabular-nums",
              totalConsumers > 0
                ? "text-indigo-600 dark:text-indigo-400"
                : "text-[hsl(var(--muted-foreground))]",
            )}
          >
            {totalConsumers}
          </p>
        </div>

        {/* Total queues */}
        <div className="flex flex-col gap-1">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Total de colas
          </p>
          <p className="text-xl font-bold tabular-nums text-foreground">
            {totalQueues}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function JobsLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {/* Banner skeleton */}
      <Skeleton className="h-14 w-full rounded-lg" />

      {/* Summary bar skeleton */}
      <Skeleton className="h-20 w-full rounded-lg" />

      {/* Queue cards grid skeleton */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-2">
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-5 w-20 rounded-full" />
              </div>
              <Skeleton className="h-3 w-24 mt-1" />
            </CardHeader>
            <CardContent className="flex flex-col gap-4 pt-0">
              <div className="rounded-lg bg-muted/50 px-4 py-3 flex flex-col items-center gap-2">
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-8 w-16" />
              </div>
              <div className="flex items-center justify-between gap-2">
                <Skeleton className="h-4 w-36" />
                <Skeleton className="h-4 w-6" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminJobsPage() {
  const {
    data: jobs,
    isLoading,
    isError,
    refetch,
    isFetching,
    dataUpdatedAt,
  } = useAdminJobs();

  // Notify on error (only when transitioning into error state, not on every render)
  const wasErrorRef = React.useRef(false);
  React.useEffect(() => {
    if (isError && !wasErrorRef.current) {
      toast.error("Error al obtener el estado de las colas", {
        description:
          "No se pudo conectar con la API. Verifica la conexion con el servidor.",
      });
    }
    wasErrorRef.current = isError;
  }, [isError]);

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Monitor de trabajos
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Estado en tiempo real de las colas RabbitMQ y sus trabajadores.
            Actualizacion automatica cada 15 segundos.
          </p>
        </div>

        {/* Manual refresh */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          aria-label="Actualizar estado de colas ahora"
        >
          <RefreshCw
            className={cn("mr-2 h-4 w-4", isFetching && "animate-spin")}
          />
          Actualizar ahora
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && <JobsLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <WifiOff className="h-10 w-10 text-red-500" aria-hidden="true" />
            <p className="font-medium text-foreground">
              No se pudo conectar con el broker de mensajes
            </p>
            <p className="text-sm text-[hsl(var(--muted-foreground))] max-w-sm">
              Verifica que RabbitMQ este en funcionamiento y que la API tenga
              acceso al broker.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Jobs content */}
      {!isLoading && !isError && jobs && (
        <>
          {/* Connection banner */}
          <ConnectionBanner data={jobs} />

          {/* Global summary bar */}
          {jobs.queues.length > 0 && (
            <SummaryStatsBar queues={jobs.queues} />
          )}

          {/* Queue cards grid */}
          {jobs.queues.length > 0 ? (
            <div>
              <div className="mb-3 flex items-center gap-2">
                <h2 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                  Colas
                </h2>
                {/* Global connection status indicator */}
                <span className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
                  {jobs.connected ? (
                    <Wifi className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <WifiOff className="h-3.5 w-3.5 text-red-500" />
                  )}
                  <span
                    className={cn(
                      "font-medium",
                      jobs.connected
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400",
                    )}
                  >
                    {jobs.connected ? "Conectado" : "Desconectado"}
                  </span>
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {jobs.queues.map((queue) => (
                  <QueueCard key={queue.name} queue={queue} />
                ))}
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
                <InboxIcon
                  className="h-8 w-8 text-[hsl(var(--muted-foreground))]"
                  aria-hidden="true"
                />
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  No se encontraron colas registradas en el broker.
                </p>
              </CardContent>
            </Card>
          )}

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
