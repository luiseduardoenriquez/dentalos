"use client";

import * as React from "react";
import {
  useMaintenanceStatus,
  useToggleMaintenance,
  type MaintenanceStatusResponse,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  MessageSquare,
  Power,
  RefreshCw,
  WrenchIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

// ─── Status Card ──────────────────────────────────────────────────────────────

interface StatusCardProps {
  status: MaintenanceStatusResponse;
  isFetching: boolean;
}

function StatusCard({ status, isFetching }: StatusCardProps) {
  const isEnabled = status.enabled;

  return (
    <Card
      className={cn(
        "border-2 transition-colors duration-300",
        isEnabled
          ? "border-red-300 dark:border-red-700/60"
          : "border-green-300 dark:border-green-700/60",
      )}
    >
      <CardContent className="pt-6 pb-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          {/* Left: icon + mode label + badge */}
          <div className="flex items-center gap-4">
            <div
              className={cn(
                "flex h-14 w-14 shrink-0 items-center justify-center rounded-full",
                isEnabled
                  ? "bg-red-100 dark:bg-red-900/30"
                  : "bg-green-100 dark:bg-green-900/30",
              )}
            >
              <WrenchIcon
                className={cn(
                  "h-7 w-7",
                  isEnabled
                    ? "text-red-600 dark:text-red-400"
                    : "text-green-600 dark:text-green-400",
                )}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                Estado actual
              </p>
              <Badge
                className={cn(
                  "w-fit px-3 py-1 text-sm font-bold",
                  isEnabled
                    ? "bg-red-100 text-red-800 hover:bg-red-100 dark:bg-red-900/40 dark:text-red-300"
                    : "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900/40 dark:text-green-300",
                )}
              >
                {isEnabled ? "Activo" : "Inactivo"}
              </Badge>
            </div>
          </div>

          {/* Right: details (message, end time, last update) */}
          <div className="flex flex-col gap-2 text-sm text-[hsl(var(--muted-foreground))]">
            {isEnabled && status.message && (
              <div className="flex items-start gap-2">
                <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
                <span className="text-foreground">{status.message}</span>
              </div>
            )}

            {isEnabled && status.scheduled_end && (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 shrink-0 text-indigo-500" />
                <span>
                  Fin programado:{" "}
                  <span className="font-medium text-foreground">
                    {formatTimestamp(status.scheduled_end)}
                  </span>
                </span>
              </div>
            )}

            {status.updated_at && (
              <div className="flex items-center gap-2">
                {isFetching ? (
                  <RefreshCw className="h-4 w-4 shrink-0 animate-spin text-indigo-400" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-indigo-400" />
                )}
                <span>
                  Ultima actualizacion:{" "}
                  <span className="font-medium text-foreground">
                    {formatTimestamp(status.updated_at)}
                  </span>
                </span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Warning Banner ───────────────────────────────────────────────────────────

function ActiveWarningBanner() {
  return (
    <div
      className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 px-5 py-4 dark:border-amber-700/50 dark:bg-amber-900/20"
      role="alert"
    >
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
      <div className="text-sm">
        <p className="font-semibold text-amber-800 dark:text-amber-300">
          Mantenimiento activo
        </p>
        <p className="mt-0.5 text-amber-700 dark:text-amber-400">
          Todas las clinicas estan viendo actualmente el banner de mantenimiento.
          Los usuarios no podran acceder al sistema hasta que se desactive el modo
          de mantenimiento.
        </p>
      </div>
    </div>
  );
}

// ─── Control Form ─────────────────────────────────────────────────────────────

interface ControlFormProps {
  isEnabled: boolean;
  isPending: boolean;
  onToggle: (payload: {
    enabled: boolean;
    message?: string;
    scheduled_end?: string;
  }) => void;
}

function ControlForm({ isEnabled, isPending, onToggle }: ControlFormProps) {
  const [message, setMessage] = React.useState("");
  const [scheduledEnd, setScheduledEnd] = React.useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: { enabled: boolean; message?: string; scheduled_end?: string } = {
      enabled: !isEnabled,
    };
    if (!isEnabled) {
      // Enabling — attach optional fields
      if (message.trim()) payload.message = message.trim();
      if (scheduledEnd) payload.scheduled_end = new Date(scheduledEnd).toISOString();
    }
    onToggle(payload);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      {/* Optional fields — only shown when about to enable */}
      {!isEnabled && (
        <>
          <div className="flex flex-col gap-2">
            <Label htmlFor="maintenance-message">
              Mensaje para los usuarios{" "}
              <span className="text-[hsl(var(--muted-foreground))]">(opcional)</span>
            </Label>
            <Textarea
              id="maintenance-message"
              placeholder="Ej: Estamos realizando mantenimiento programado. Regresaremos en breve."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              className="resize-none"
              disabled={isPending}
            />
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Este mensaje sera visible en el banner de mantenimiento que ven los usuarios.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="scheduled-end">
              Fin programado{" "}
              <span className="text-[hsl(var(--muted-foreground))]">(opcional)</span>
            </Label>
            <Input
              id="scheduled-end"
              type="datetime-local"
              value={scheduledEnd}
              onChange={(e) => setScheduledEnd(e.target.value)}
              disabled={isPending}
              className="max-w-xs"
            />
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Hora estimada de reactivacion del sistema.
            </p>
          </div>
        </>
      )}

      {/* Toggle button */}
      <div>
        <Button
          type="submit"
          variant={isEnabled ? "default" : "destructive"}
          disabled={isPending}
          className={cn(
            "gap-2",
            !isEnabled && "bg-red-600 hover:bg-red-700 focus-visible:ring-red-500",
            isEnabled &&
              "bg-green-600 hover:bg-green-700 focus-visible:ring-green-500 text-white",
          )}
        >
          {isPending ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Power className="h-4 w-4" />
          )}
          {isPending
            ? isEnabled
              ? "Desactivando..."
              : "Activando..."
            : isEnabled
              ? "Desactivar mantenimiento"
              : "Activar mantenimiento"}
        </Button>
      </div>
    </form>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function MaintenanceLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-32 w-full rounded-xl" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminMaintenancePage() {
  const {
    data: status,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useMaintenanceStatus();

  const toggleMutation = useToggleMaintenance();

  function handleToggle(payload: {
    enabled: boolean;
    message?: string;
    scheduled_end?: string;
  }) {
    toggleMutation.mutate(payload, {
      onSuccess: (data) => {
        if (data.enabled) {
          toast.success("Modo de mantenimiento activado", {
            description: "Todos los usuarios veran el banner de mantenimiento.",
          });
        } else {
          toast.success("Modo de mantenimiento desactivado", {
            description: "El sistema esta operativo para todos los usuarios.",
          });
        }
      },
      onError: () => {
        toast.error("Error al cambiar el modo de mantenimiento", {
          description: "Verifica la conexion con la API e intenta nuevamente.",
        });
      },
    });
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Modo de mantenimiento
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Activa o desactiva el modo de mantenimiento para todas las clinicas.
            Actualizacion automatica cada 30 segundos.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          aria-label="Actualizar estado"
        >
          <RefreshCw
            className={cn("mr-2 h-4 w-4", isFetching && "animate-spin")}
          />
          Actualizar
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && <MaintenanceLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar el estado del mantenimiento. Verifica la conexion
              con la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Main content */}
      {!isLoading && !isError && status && (
        <>
          {/* Status card */}
          <StatusCard status={status} isFetching={isFetching} />

          {/* Active warning banner */}
          {status.enabled && <ActiveWarningBanner />}

          {/* Control card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {status.enabled ? "Desactivar mantenimiento" : "Activar mantenimiento"}
              </CardTitle>
              <CardDescription>
                {status.enabled
                  ? "Al desactivar, todos los usuarios recuperaran acceso al sistema de inmediato."
                  : "Al activar, todos los usuarios veran un banner de mantenimiento y no podran iniciar sesion."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ControlForm
                isEnabled={status.enabled}
                isPending={toggleMutation.isPending}
                onToggle={handleToggle}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
