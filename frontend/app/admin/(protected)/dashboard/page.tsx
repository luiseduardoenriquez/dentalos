"use client";

/**
 * Admin dashboard page — platform-wide metrics and system health.
 *
 * Sections:
 * 1. Four KPI cards: total clinics, MRR, total users, system status.
 * 2. Four service health dots: PostgreSQL, Redis, RabbitMQ, Storage.
 * 3. Recent tenants table (last 5 from the list, sorted by created_at desc).
 */

import Link from "next/link";
import { Building2, DollarSign, Users, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  useAdminAnalytics,
  useAdminHealth,
  useAdminTenants,
  type TenantSummary,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatMrr(cents: number): string {
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  isLoading?: boolean;
  /** Optional badge to show instead of the subtitle */
  statusBadge?: React.ReactNode;
}

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconBg,
  iconColor,
  isLoading,
  statusBadge,
}: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <div
            className={cn(
              "flex items-center justify-center w-9 h-9 rounded-lg shrink-0",
              iconBg,
            )}
            aria-hidden="true"
          >
            <Icon className={cn("h-4 w-4", iconColor)} />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <>
            <Skeleton className="h-8 w-28 mb-1" />
            <Skeleton className="h-3 w-20" />
          </>
        ) : (
          <>
            <p className="text-3xl font-bold text-foreground tabular-nums">
              {value}
            </p>
            {statusBadge ? (
              <div className="mt-1">{statusBadge}</div>
            ) : subtitle ? (
              <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Service Health Dot ───────────────────────────────────────────────────────

interface ServiceDotProps {
  label: string;
  /** "ok" = green, "error" = red, "unknown" = gray */
  status: "ok" | "error" | "unknown";
  isLoading?: boolean;
}

function ServiceDot({ label, status, isLoading }: ServiceDotProps) {
  const dotClass =
    status === "ok"
      ? "bg-green-500"
      : status === "error"
        ? "bg-red-500"
        : "bg-slate-400";

  const dotLabel =
    status === "ok" ? "Conectado" : status === "error" ? "Sin conexion" : "Desconocido";

  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        {isLoading ? (
          <div className="flex items-center gap-2">
            <Skeleton className="h-2.5 w-2.5 rounded-full" />
            <Skeleton className="h-4 w-24" />
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span
              className={cn("inline-block h-2.5 w-2.5 rounded-full shrink-0", dotClass)}
              aria-hidden="true"
            />
            <div>
              <p className="text-xs font-semibold text-foreground">{label}</p>
              <p className="text-xs text-muted-foreground">{dotLabel}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Tenant Status Badge ──────────────────────────────────────────────────────

function TenantStatusBadge({ status }: { status: string }) {
  const map: Record<string, React.ComponentProps<typeof Badge>["variant"]> = {
    active: "success",
    trial: "warning",
    suspended: "destructive",
    cancelled: "outline",
  };
  const labels: Record<string, string> = {
    active: "Activa",
    trial: "Trial",
    suspended: "Suspendida",
    cancelled: "Cancelada",
  };
  return (
    <Badge variant={map[status] ?? "outline"}>
      {labels[status] ?? status}
    </Badge>
  );
}

// ─── Plan Badge ───────────────────────────────────────────────────────────────

function PlanBadge({ plan }: { plan: string }) {
  const planColors: Record<string, string> = {
    free: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
    starter:
      "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700/40",
    pro: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-700/40",
    clinica:
      "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-700/40",
    enterprise:
      "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700/40",
  };
  const normalized = plan.toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border",
        planColors[normalized] ?? planColors.free,
      )}
    >
      {plan}
    </span>
  );
}

// ─── Recent Tenants Table ─────────────────────────────────────────────────────

function RecentTenantsTable({
  tenants,
  isLoading,
}: {
  tenants: TenantSummary[];
  isLoading: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Clinicas recientes</CardTitle>
        <CardDescription>
          Las ultimas 5 clinicas registradas en la plataforma
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" aria-label="Clinicas recientes">
            <thead>
              <tr className="border-b border-[hsl(var(--border))]">
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Plan
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Estado
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Usuarios
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Creado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="px-6 py-3">
                        <Skeleton className="h-4 w-36" />
                      </td>
                      <td className="px-6 py-3">
                        <Skeleton className="h-5 w-16 rounded-full" />
                      </td>
                      <td className="px-6 py-3">
                        <Skeleton className="h-5 w-16 rounded-full" />
                      </td>
                      <td className="px-6 py-3">
                        <Skeleton className="h-4 w-8 ml-auto" />
                      </td>
                      <td className="px-6 py-3">
                        <Skeleton className="h-4 w-24" />
                      </td>
                    </tr>
                  ))
                : tenants.map((tenant) => (
                    <tr
                      key={tenant.id}
                      className="hover:bg-[hsl(var(--muted))] transition-colors"
                    >
                      <td className="px-6 py-3 font-medium text-foreground">
                        <Link
                          href={`/admin/tenants/${tenant.id}`}
                          className="hover:underline text-primary-600 dark:text-primary-400"
                        >
                          {tenant.name}
                        </Link>
                      </td>
                      <td className="px-6 py-3">
                        <PlanBadge plan={tenant.plan_name} />
                      </td>
                      <td className="px-6 py-3">
                        <TenantStatusBadge status={tenant.status} />
                      </td>
                      <td className="px-6 py-3 text-right tabular-nums text-foreground">
                        {tenant.user_count}
                      </td>
                      <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                        {formatDate(tenant.created_at)}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>

          {!isLoading && tenants.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No hay clinicas registradas aun.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Admin dashboard page.
 *
 * Data sources:
 * - useAdminAnalytics → platform KPIs (MRR, tenant/user counts).
 * - useAdminHealth → system service status (postgres, redis, rabbitmq, storage).
 * - useAdminTenants({ page: 1, page_size: 5 }) → last 5 tenants for the table.
 *
 * Error handling: each section handles its own error state independently so
 * a health endpoint failure does not break the metrics cards.
 */
export default function AdminDashboardPage() {
  const {
    data: analytics,
    isLoading: analyticsLoading,
    isError: analyticsError,
    refetch: refetchAnalytics,
  } = useAdminAnalytics();

  const {
    data: health,
    isLoading: healthLoading,
    isError: healthError,
    refetch: refetchHealth,
  } = useAdminHealth();

  const {
    data: recentTenants,
    isLoading: tenantsLoading,
  } = useAdminTenants({ page: 1, page_size: 5 });

  // ── Derive system overall status for the KPI card ─────────────────────────
  const systemStatusLabel =
    healthLoading
      ? "..."
      : !health
        ? "Error"
        : health.status === "healthy"
          ? "Saludable"
          : "Degradado";

  const systemStatusBadge = !healthLoading && health ? (
    <Badge variant={health.status === "healthy" ? "success" : "warning"}>
      {systemStatusLabel}
    </Badge>
  ) : null;

  // ── Resolve service health from flat booleans ─────────────────────────────
  function serviceStatus(up: boolean | undefined): "ok" | "error" | "unknown" {
    if (up === undefined) return "unknown";
    return up ? "ok" : "error";
  }

  return (
    <div className="space-y-8">
      {/* ── Page title ── */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          Panel de administracion
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Metricas de la plataforma en tiempo real.
        </p>
      </div>

      {/* ── Analytics error state ── */}
      {analyticsError && (
        <Card className="border-destructive-200 dark:border-destructive-700/40">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive-600 dark:text-destructive-400">
              No se pudieron cargar las metricas de la plataforma.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => refetchAnalytics()}
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── KPI cards ── */}
      <section aria-label="Metricas de la plataforma">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <KpiCard
            title="Total clinicas"
            value={String(analytics?.total_tenants ?? 0)}
            subtitle={
              analytics
                ? `${analytics.active_tenants} activas`
                : undefined
            }
            icon={Building2}
            iconBg="bg-indigo-50 dark:bg-indigo-900/30"
            iconColor="text-indigo-600 dark:text-indigo-400"
            isLoading={analyticsLoading}
          />
          <KpiCard
            title="MRR"
            value={analytics ? formatMrr(analytics.mrr_cents) : "$0.00"}
            subtitle="Recurrente mensual"
            icon={DollarSign}
            iconBg="bg-emerald-50 dark:bg-emerald-900/30"
            iconColor="text-emerald-600 dark:text-emerald-400"
            isLoading={analyticsLoading}
          />
          <KpiCard
            title="Usuarios activos"
            value={String(analytics?.total_users ?? 0)}
            subtitle={
              analytics
                ? `${analytics.total_patients.toLocaleString("es-CO")} pacientes en total`
                : undefined
            }
            icon={Users}
            iconBg="bg-sky-50 dark:bg-sky-900/30"
            iconColor="text-sky-600 dark:text-sky-400"
            isLoading={analyticsLoading}
          />
          <KpiCard
            title="Estado del sistema"
            value={systemStatusLabel}
            icon={Activity}
            iconBg={
              health?.status === "healthy"
                ? "bg-emerald-50 dark:bg-emerald-900/30"
                : "bg-amber-50 dark:bg-amber-900/30"
            }
            iconColor={
              health?.status === "healthy"
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-amber-600 dark:text-amber-400"
            }
            isLoading={healthLoading}
            statusBadge={systemStatusBadge}
          />
        </div>
      </section>

      {/* ── Health error state ── */}
      {healthError && (
        <Card className="border-destructive-200 dark:border-destructive-700/40">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive-600 dark:text-destructive-400">
              No se pudo obtener el estado del sistema.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => refetchHealth()}
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Service health row ── */}
      <section aria-label="Estado de servicios">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
          Estado de servicios
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <ServiceDot
            label="PostgreSQL"
            status={serviceStatus(health?.postgres)}
            isLoading={healthLoading}
          />
          <ServiceDot
            label="Redis"
            status={serviceStatus(health?.redis)}
            isLoading={healthLoading}
          />
          <ServiceDot
            label="RabbitMQ"
            status={serviceStatus(health?.rabbitmq)}
            isLoading={healthLoading}
          />
          <ServiceDot
            label="Storage"
            status={serviceStatus(health?.storage)}
            isLoading={healthLoading}
          />
        </div>
      </section>

      {/* ── Recent tenants ── */}
      <section aria-label="Clinicas recientes">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Clinicas recientes
          </h2>
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/tenants">Ver todas</Link>
          </Button>
        </div>
        <RecentTenantsTable
          tenants={recentTenants?.items ?? []}
          isLoading={tenantsLoading}
        />
      </section>
    </div>
  );
}
