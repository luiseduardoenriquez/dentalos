"use client";

/**
 * Admin trial management page (SA-R02).
 *
 * Features:
 * - KPI cards: total trials, expiring soon (next 7 days), conversion rate (%).
 * - Table listing all trial tenants with key metadata.
 * - "Dias restantes" badge: red (<=3), yellow (<=7), green (>7).
 * - Extend-trial dialog per row: input for days, default 14.
 * - Loading skeleton while data loads.
 * - Error state with retry button.
 */

import React, { useState } from "react";
import {
  Clock,
  AlertTriangle,
  TrendingUp,
  CalendarClock,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useAdminTrials,
  useExtendTrial,
  type TrialTenantItem,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

// ─── Days Remaining Badge ─────────────────────────────────────────────────────

function DaysRemainingBadge({ days }: { days: number | null }) {
  if (days === null) {
    return (
      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
        —
      </span>
    );
  }

  const className =
    days <= 3
      ? "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/40"
      : days <= 7
        ? "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700/40"
        : "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/40";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border tabular-nums",
        className,
      )}
    >
      {days <= 0 ? "Vencido" : `${days}d`}
    </span>
  );
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

const STATUS_VARIANTS: Record<string, React.ComponentProps<typeof Badge>["variant"]> = {
  active: "success",
  trial: "warning",
  suspended: "destructive",
  cancelled: "outline",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Activa",
  trial: "Trial",
  suspended: "Suspendida",
  cancelled: "Cancelada",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={STATUS_VARIANTS[status] ?? "outline"}>
      {STATUS_LABELS[status] ?? status}
    </Badge>
  );
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: string;
  icon: React.ElementType;
  iconClassName?: string;
  valueClassName?: string;
}

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconClassName,
  valueClassName,
}: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <CardDescription className="text-xs font-medium uppercase tracking-wide">
          {title}
        </CardDescription>
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            iconClassName ?? "bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400",
          )}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </CardHeader>
      <CardContent>
        <p
          className={cn(
            "text-3xl font-bold tabular-nums tracking-tight text-foreground",
            valueClassName,
          )}
        >
          {value}
        </p>
        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── KPI Skeleton ─────────────────────────────────────────────────────────────

function KpiCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-9 w-20" />
        <Skeleton className="mt-2 h-3 w-32" />
      </CardContent>
    </Card>
  );
}

// ─── Extend Trial Dialog ──────────────────────────────────────────────────────

interface ExtendTrialDialogProps {
  tenant: TrialTenantItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function ExtendTrialDialog({ tenant, open, onOpenChange }: ExtendTrialDialogProps) {
  const [days, setDays] = useState("14");
  const { mutate: extendTrial, isPending } = useExtendTrial();

  function handleClose() {
    onOpenChange(false);
    setDays("14");
  }

  function handleSubmit() {
    if (!tenant) return;

    const parsedDays = parseInt(days, 10);
    if (isNaN(parsedDays) || parsedDays < 1 || parsedDays > 365) {
      toast.error("Ingresa un numero de dias valido entre 1 y 365.");
      return;
    }

    extendTrial(
      { tenantId: tenant.id, days: parsedDays },
      {
        onSuccess: (data) => {
          toast.success(
            `Trial de "${tenant.name}" extendido ${data.days_added} dias. Nuevo vencimiento: ${formatDate(data.trial_ends_at)}.`,
          );
          handleClose();
        },
        onError: (err) => {
          toast.error(
            err instanceof Error
              ? err.message
              : "No se pudo extender el trial. Intentalo de nuevo.",
          );
        },
      },
    );
  }

  function handleDaysChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value.replace(/[^0-9]/g, "");
    setDays(raw);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Extender trial</DialogTitle>
          <DialogDescription>
            {tenant ? (
              <>
                Extiende el periodo de prueba de{" "}
                <span className="font-semibold text-foreground">{tenant.name}</span>.
                {tenant.days_remaining !== null && tenant.days_remaining > 0 && (
                  <> Actualmente le quedan{" "}
                    <span className="font-semibold">{tenant.days_remaining} dias</span>.</>
                )}
              </>
            ) : (
              "Extiende el periodo de prueba de esta clinica."
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="extend-days">
              Dias adicionales <span className="text-destructive">*</span>
            </Label>
            <Input
              id="extend-days"
              type="number"
              min={1}
              max={365}
              value={days}
              onChange={handleDaysChange}
              placeholder="14"
              disabled={isPending}
              autoFocus
              className="text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Minimo 1 dia, maximo 365 dias.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={isPending || !days || parseInt(days, 10) < 1}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            {isPending ? "Extendiendo..." : "Confirmar extension"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Trials Table ─────────────────────────────────────────────────────────────

interface TrialsTableProps {
  items: TrialTenantItem[];
  isLoading: boolean;
  onExtend: (tenant: TrialTenantItem) => void;
}

const SKELETON_ROWS = 6;

function TrialsTable({ items, isLoading, onExtend }: TrialsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" aria-label="Lista de clinicas en trial">
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Clinica
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Plan
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Email
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Dias restantes
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Estado
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Fecha inicio
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {isLoading
            ? Array.from({ length: SKELETON_ROWS }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <Skeleton className="h-4 w-36" />
                      <Skeleton className="h-3 w-24" />
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-40" />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Skeleton className="h-5 w-12 rounded-full mx-auto" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-24" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Skeleton className="h-8 w-20 ml-auto rounded-md" />
                  </td>
                </tr>
              ))
            : items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-[hsl(var(--muted))] transition-colors"
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-foreground leading-tight">
                        {item.name}
                      </p>
                      <code className="text-xs font-mono text-muted-foreground bg-[hsl(var(--muted))] px-1.5 py-0.5 rounded mt-0.5 inline-block">
                        {item.slug}
                      </code>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-700/40">
                      {item.plan_name}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-sm">
                    {item.owner_email}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <DaysRemainingBadge days={item.days_remaining} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onExtend(item)}
                      className="text-indigo-600 border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 dark:text-indigo-400 dark:border-indigo-700/40 dark:hover:bg-indigo-900/30"
                    >
                      <CalendarClock className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
                      Extender
                    </Button>
                  </td>
                </tr>
              ))}
        </tbody>
      </table>

      {!isLoading && items.length === 0 && (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No hay clinicas en periodo de trial en este momento.
        </p>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminTrialsPage() {
  const [selectedTenant, setSelectedTenant] = useState<TrialTenantItem | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading, isError, refetch } = useAdminTrials();

  function handleExtend(tenant: TrialTenantItem) {
    setSelectedTenant(tenant);
    setDialogOpen(true);
  }

  function handleDialogOpenChange(open: boolean) {
    setDialogOpen(open);
    if (!open) {
      setSelectedTenant(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Gestion de Trials</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {data
              ? `${data.total} clinicas en periodo de prueba`
              : "Monitorea y gestiona los periodos de prueba de las clinicas."}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading}
          aria-label="Actualizar datos de trials"
        >
          <RefreshCw
            className={cn("h-3.5 w-3.5 mr-1.5", isLoading && "animate-spin")}
            aria-hidden="true"
          />
          Actualizar
        </Button>
      </div>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {isLoading ? (
          <>
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
          </>
        ) : (
          <>
            <KpiCard
              title="Total en trial"
              value={data?.total ?? 0}
              subtitle="Clinicas actualmente en periodo de prueba"
              icon={Clock}
              iconClassName="bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400"
            />
            <KpiCard
              title="Vencen pronto"
              value={data?.expiring_soon_count ?? 0}
              subtitle="Clinicas con trial que vence en los proximos 7 dias"
              icon={AlertTriangle}
              iconClassName={
                (data?.expiring_soon_count ?? 0) > 0
                  ? "bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400"
                  : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
              }
              valueClassName={
                (data?.expiring_soon_count ?? 0) > 0
                  ? "text-yellow-600 dark:text-yellow-400"
                  : undefined
              }
            />
            <KpiCard
              title="Tasa de conversion"
              value={formatPercent(data?.conversion_rate ?? 0)}
              subtitle={
                data?.avg_days_to_conversion
                  ? `Promedio ${data.avg_days_to_conversion.toFixed(0)} dias hasta conversion`
                  : "Porcentaje de trials que se convierten a plan pago"
              }
              icon={TrendingUp}
              iconClassName="bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
              valueClassName="text-green-600 dark:text-green-400"
            />
          </>
        )}
      </div>

      {/* ── Error state ── */}
      {isError && (
        <Card className="border-destructive/40">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertTriangle
                className="h-5 w-5 text-destructive mt-0.5 shrink-0"
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-medium text-foreground">
                  No se pudo cargar la lista de trials
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Verifica tu conexion o contacta al equipo de infraestructura si el problema persiste.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => refetch()}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
                  Reintentar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Table ── */}
      {!isError && (
        <Card className="overflow-hidden">
          <TrialsTable
            items={data?.items ?? []}
            isLoading={isLoading}
            onExtend={handleExtend}
          />
        </Card>
      )}

      {/* ── Extend Trial Dialog ── */}
      <ExtendTrialDialog
        tenant={selectedTenant}
        open={dialogOpen}
        onOpenChange={handleDialogOpenChange}
      />
    </div>
  );
}
