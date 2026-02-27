"use client";

import * as React from "react";
import { useAdminHealth, type SystemHealthResponse } from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw } from "lucide-react";
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

// ─── Service Card ──────────────────────────────────────────────────────────────

interface ServiceCardProps {
  label: string;
  connected: boolean;
}

function ServiceCard({ label, connected }: ServiceCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-5">
        {/* Status dot */}
        <span
          className={cn(
            "h-4 w-4 rounded-full shrink-0",
            connected ? "bg-green-500" : "bg-red-500",
          )}
          aria-hidden="true"
        />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground">{label}</p>
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
      </CardContent>
    </Card>
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

      {/* Service cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="flex items-center gap-4 py-5">
              <Skeleton className="h-4 w-4 rounded-full shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-3 w-16" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Service Definitions ───────────────────────────────────────────────────────

type ServiceKey = "postgres" | "redis" | "rabbitmq" | "storage";

const SERVICES: Array<{ key: ServiceKey; label: string }> = [
  { key: "postgres", label: "PostgreSQL" },
  { key: "redis", label: "Redis" },
  { key: "rabbitmq", label: "RabbitMQ" },
  { key: "storage", label: "Almacenamiento" },
];

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

          {/* Service cards grid */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
              Servicios
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {SERVICES.map(({ key, label }) => (
                <ServiceCard
                  key={key}
                  label={label}
                  connected={health[key]}
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
