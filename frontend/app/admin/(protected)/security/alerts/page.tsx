"use client";

/**
 * Admin security alerts page (SA-C02).
 *
 * Displays a 24-hour window of platform security events: failed logins,
 * suspicious IPs, and after-hours actions. KPI summary cards at the top,
 * followed by a sortable list of individual alert cards.
 *
 * Data auto-refreshes every 5 minutes via the hook's refetchInterval.
 */

import { AlertTriangle, AlertCircle, Info, CheckCircle2, RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useSecurityAlerts,
  type SecurityAlertListResponse,
  type SecurityAlertItem,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Severity sort order: critical=0 (highest), warning=1, info=2 */
const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

const ALERT_TYPE_LABELS: Record<string, string> = {
  failed_login: "Inicio fallido",
  suspicious_ip: "IP sospechosa",
  after_hours: "Fuera de horario",
  rate_limit: "Límite de tasa",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Formats an ISO timestamp as a relative time string in Spanish when the event
 * is less than 24 hours old, otherwise as a full date/time (es-419).
 */
function formatRelativeOrDate(iso: string): string {
  try {
    const date = new Date(iso);
    const now = Date.now();
    const diffMs = now - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);

    if (diffMins < 1) return "Hace un momento";
    if (diffMins < 60) return `Hace ${diffMins} min`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) {
      return `Hace ${diffHours} ${diffHours === 1 ? "hora" : "horas"}`;
    }

    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  } catch {
    return iso;
  }
}

/**
 * Sorts alert items: critical first, then warning, then info.
 * Within the same severity, more recent items come first.
 */
function sortAlerts(items: SecurityAlertItem[]): SecurityAlertItem[] {
  return [...items].sort((a, b) => {
    const severityDiff =
      (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99);
    if (severityDiff !== 0) return severityDiff;
    // Same severity — sort descending by created_at
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

// ─── KPI Cards ────────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string;
  value: number;
  variant: "red" | "amber" | "neutral";
  isLoading: boolean;
}

function KpiCard({ label, value, variant, isLoading }: KpiCardProps) {
  const valueClasses = cn(
    "text-3xl font-bold tabular-nums",
    variant === "red" && value > 0 && "text-red-600 dark:text-red-400",
    variant === "amber" && value > 0 && "text-amber-600 dark:text-amber-400",
    (variant === "neutral" || value === 0) && "text-foreground",
  );

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-5 py-4">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-4 w-32" />
        </div>
      ) : (
        <>
          <p className={valueClasses}>{value.toLocaleString("es-419")}</p>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{label}</p>
        </>
      )}
    </div>
  );
}

// ─── Severity Icon ────────────────────────────────────────────────────────────

function SeverityIcon({ severity }: { severity: string }) {
  if (severity === "critical") {
    return (
      <AlertTriangle
        className="h-5 w-5 shrink-0 text-red-500 dark:text-red-400"
        aria-label="Critico"
      />
    );
  }
  if (severity === "warning") {
    return (
      <AlertCircle
        className="h-5 w-5 shrink-0 text-amber-500 dark:text-amber-400"
        aria-label="Advertencia"
      />
    );
  }
  return (
    <Info
      className="h-5 w-5 shrink-0 text-blue-500 dark:text-blue-400"
      aria-label="Informacion"
    />
  );
}

// ─── Alert Type Badge ─────────────────────────────────────────────────────────

function alertTypeBadgeClasses(alertType: string): string {
  switch (alertType) {
    case "failed_login":
      return "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300";
    case "suspicious_ip":
      return "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300";
    case "after_hours":
      return "border-orange-300 bg-orange-50 text-orange-700 dark:border-orange-700 dark:bg-orange-950 dark:text-orange-300";
    case "rate_limit":
      return "border-purple-300 bg-purple-50 text-purple-700 dark:border-purple-700 dark:bg-purple-950 dark:text-purple-300";
    default:
      return "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300";
  }
}

function AlertTypeBadge({ alertType }: { alertType: string }) {
  const label = ALERT_TYPE_LABELS[alertType] ?? alertType;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        alertTypeBadgeClasses(alertType),
      )}
    >
      {label}
    </span>
  );
}

// ─── Single Alert Card ────────────────────────────────────────────────────────

function AlertCard({ alert }: { alert: SecurityAlertItem }) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-[hsl(var(--card))] px-4 py-3",
        alert.severity === "critical" &&
          "border-red-200 dark:border-red-800/50",
        alert.severity === "warning" &&
          "border-amber-200 dark:border-amber-800/50",
        alert.severity === "info" &&
          "border-[hsl(var(--border))]",
      )}
      role="listitem"
    >
      <div className="flex items-start gap-3">
        {/* Severity icon */}
        <div className="mt-0.5">
          <SeverityIcon severity={alert.severity} />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1 space-y-1.5">
          {/* Top row: badge + timestamp */}
          <div className="flex flex-wrap items-center gap-2">
            <AlertTypeBadge alertType={alert.alert_type} />
            <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums">
              {formatRelativeOrDate(alert.created_at)}
            </span>
          </div>

          {/* Message */}
          <p className="text-sm text-foreground leading-snug">{alert.message}</p>

          {/* Source IP (optional) */}
          {alert.source_ip && (
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              IP:{" "}
              <code className="font-mono text-foreground bg-[hsl(var(--muted))] px-1.5 py-0.5 rounded text-xs">
                {alert.source_ip}
              </code>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function AlertsLoadingSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Cargando alertas">
      {/* KPI skeleton */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-5 py-4 space-y-2"
          >
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-4 w-36" />
          </div>
        ))}
      </div>

      {/* Alert card skeletons */}
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-4 py-3"
          >
            <div className="flex items-start gap-3">
              <Skeleton className="mt-0.5 h-5 w-5 rounded-full shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-5 w-28 rounded-full" />
                  <Skeleton className="h-4 w-20" />
                </div>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-40" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] py-16 text-center"
      role="status"
    >
      <CheckCircle2
        className="h-10 w-10 text-green-500 dark:text-green-400"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-foreground">
        No se detectaron alertas de seguridad en las últimas 24 horas
      </p>
      <p className="text-xs text-[hsl(var(--muted-foreground))] max-w-xs">
        El sistema monitorea inicios de sesión fallidos, IPs sospechosas y acciones fuera de horario en tiempo real.
      </p>
    </div>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          No se pudo cargar las alertas de seguridad.
        </p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Reintentar
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SecurityAlertsPage() {
  const { data, isLoading, isError, refetch, isFetching } = useSecurityAlerts(1, 50);

  const sortedAlerts: SecurityAlertItem[] = data ? sortAlerts(data.items) : [];

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Alertas de Seguridad
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Monitoreo de eventos de seguridad en las últimas 24 horas
          </p>
        </div>

        {/* Auto-refresh badge + manual refresh */}
        <div className="flex items-center gap-3 shrink-0">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-1 text-xs text-[hsl(var(--muted-foreground))]">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                isFetching ? "bg-amber-400 animate-pulse" : "bg-green-500",
              )}
              aria-hidden="true"
            />
            Actualización cada 5 min
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            aria-label="Actualizar alertas ahora"
          >
            <RefreshCw
              className={cn("mr-2 h-3.5 w-3.5", isFetching && "animate-spin")}
              aria-hidden="true"
            />
            Actualizar
          </Button>
        </div>
      </div>

      {/* ── Loading skeleton ── */}
      {isLoading && <AlertsLoadingSkeleton />}

      {/* ── Error state ── */}
      {isError && !isLoading && <ErrorState onRetry={() => refetch()} />}

      {/* ── Loaded content ── */}
      {!isLoading && !isError && data && (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard
              label="Inicios de sesión fallidos"
              value={data.failed_logins_24h}
              variant="red"
              isLoading={false}
            />
            <KpiCard
              label="IPs sospechosas"
              value={data.suspicious_ips}
              variant="red"
              isLoading={false}
            />
            <KpiCard
              label="Acciones fuera de horario"
              value={data.after_hours_actions}
              variant="amber"
              isLoading={false}
            />
          </div>

          {/* Alerts list */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                Eventos detectados
              </h2>
              {data.total > 0 && (
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                  {data.total} {data.total === 1 ? "alerta" : "alertas"}
                </span>
              )}
            </div>

            {sortedAlerts.length === 0 ? (
              <EmptyState />
            ) : (
              <div
                className="space-y-3"
                role="list"
                aria-label="Lista de alertas de seguridad"
              >
                {sortedAlerts.map((alert) => (
                  <AlertCard key={alert.id} alert={alert} />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
