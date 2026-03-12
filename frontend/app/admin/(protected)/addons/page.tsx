"use client";

/**
 * Admin add-on usage tracking page (SA-R03).
 *
 * Features:
 * - KPI cards: eligible tenants, AI Voice adoption, AI Radiograph adoption, total add-on revenue.
 * - Two add-on detail cards (AI Voice + AI Radiograph) with adoption percentage bar.
 * - Upsell candidates highlight banner.
 * - Tenant table: clinic name, plan, AI Voice status badge, AI Radiograph status badge.
 * - Loading skeleton while data loads.
 * - Error state with retry button.
 */

import React from "react";
import {
  Mic,
  ScanLine,
  TrendingUp,
  Users,
  DollarSign,
  Target,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAddonUsage,
  type AddonMetrics,
  type AddonTenantUsage,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const formatUSD = (cents: number): string =>
  "$" + (cents / 100).toLocaleString("en-US", { minimumFractionDigits: 0 });

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
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
            iconClassName ??
              "bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400",
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
        <Skeleton className="h-9 w-24" />
        <Skeleton className="mt-2 h-3 w-36" />
      </CardContent>
    </Card>
  );
}

// ─── Adoption Bar ─────────────────────────────────────────────────────────────

interface AdoptionBarProps {
  pct: number;
  /** Tailwind bg color class for the filled portion */
  fillClassName?: string;
}

function AdoptionBar({ pct, fillClassName = "bg-indigo-500" }: AdoptionBarProps) {
  const clamped = Math.min(100, Math.max(0, pct));
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-[hsl(var(--muted))]">
      <div
        className={cn("h-2.5 rounded-full transition-all duration-500", fillClassName)}
        style={{ width: `${clamped.toFixed(1)}%` }}
      />
    </div>
  );
}

// ─── Add-on Detail Card ───────────────────────────────────────────────────────

interface AddonDetailCardProps {
  title: string;
  price: string;
  adoptionPct: number;
  adoptionCount: number;
  totalEligible: number;
  revenueCents: number;
  icon: React.ElementType;
  accentClassName: string;
  barFillClassName: string;
}

function AddonDetailCard({
  title,
  price,
  adoptionPct,
  adoptionCount,
  totalEligible,
  revenueCents,
  icon: Icon,
  accentClassName,
  barFillClassName,
}: AddonDetailCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-lg",
                accentClassName,
              )}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold leading-tight">
                {title}
              </CardTitle>
              <CardDescription className="text-xs">{price}</CardDescription>
            </div>
          </div>
          <span className="text-2xl font-bold tabular-nums tracking-tight text-foreground">
            {formatPercent(adoptionPct)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Adoption progress bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Adopcion</span>
            <span className="tabular-nums">
              {adoptionCount} / {totalEligible} clinicas
            </span>
          </div>
          <AdoptionBar pct={adoptionPct} fillClassName={barFillClassName} />
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div className="rounded-lg bg-[hsl(var(--muted))] px-3 py-2">
            <p className="text-xs text-muted-foreground">Clinicas activas</p>
            <p className="mt-0.5 text-lg font-bold tabular-nums text-foreground">
              {adoptionCount}
            </p>
          </div>
          <div className="rounded-lg bg-[hsl(var(--muted))] px-3 py-2">
            <p className="text-xs text-muted-foreground">Ingresos (MRR)</p>
            <p className="mt-0.5 text-lg font-bold tabular-nums text-foreground">
              {formatUSD(revenueCents)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Upsell Candidates Banner ─────────────────────────────────────────────────

function UpsellBanner({ count }: { count: number }) {
  if (count === 0) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50/60 px-4 py-3 dark:border-green-700/40 dark:bg-green-900/10">
        <CheckCircle2
          className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0"
          aria-hidden="true"
        />
        <p className="text-sm text-green-800 dark:text-green-300">
          <span className="font-semibold">Sin candidatos de upsell</span> — todas
          las clinicas elegibles ya tienen al menos un add-on activo.
        </p>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 rounded-lg border border-indigo-200 bg-indigo-50/60 px-4 py-3 dark:border-indigo-700/40 dark:bg-indigo-900/10">
      <Target
        className="h-5 w-5 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5"
        aria-hidden="true"
      />
      <div>
        <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">
          {count} {count === 1 ? "clinica candidata" : "clinicas candidatas"} a
          upsell
        </p>
        <p className="mt-0.5 text-xs text-indigo-700 dark:text-indigo-400">
          Estas clinicas estan en un plan compatible pero aun no tienen ningun
          add-on activo. Contactarlas puede incrementar el MRR.
        </p>
      </div>
    </div>
  );
}

// ─── Addon Status Badge ───────────────────────────────────────────────────────

function AddonBadge({ enabled }: { enabled: boolean }) {
  if (enabled) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold border bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/40">
        <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
        Activo
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold border bg-slate-50 text-slate-500 border-slate-200 dark:bg-slate-800/50 dark:text-slate-400 dark:border-slate-700">
      <XCircle className="h-3 w-3" aria-hidden="true" />
      Inactivo
    </span>
  );
}

// ─── Tenant Table ─────────────────────────────────────────────────────────────

interface TenantTableProps {
  tenants: AddonTenantUsage[];
  isLoading: boolean;
}

const SKELETON_ROWS = 7;

function TenantTable({ tenants, isLoading }: TenantTableProps) {
  return (
    <div className="overflow-x-auto">
      <table
        className="w-full text-sm"
        aria-label="Uso de add-ons por clinica"
      >
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Clinica
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Plan
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wide">
              AI Voice
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wide">
              AI Radiografia
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {isLoading
            ? Array.from({ length: SKELETON_ROWS }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-40" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-20 rounded-full" />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Skeleton className="h-5 w-16 rounded-full mx-auto" />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Skeleton className="h-5 w-16 rounded-full mx-auto" />
                  </td>
                </tr>
              ))
            : tenants.map((t) => (
                <tr
                  key={t.tenant_id}
                  className="hover:bg-[hsl(var(--muted))] transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className="font-medium text-foreground leading-tight">
                      {t.tenant_name}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-700/40">
                      {t.plan_name}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <AddonBadge enabled={t.voice_enabled} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <AddonBadge enabled={t.radiograph_enabled} />
                  </td>
                </tr>
              ))}
        </tbody>
      </table>

      {!isLoading && tenants.length === 0 && (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No hay clinicas elegibles para add-ons en este momento.
        </p>
      )}
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function AddonsLoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* KPI skeletons */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCardSkeleton />
        <KpiCardSkeleton />
        <KpiCardSkeleton />
        <KpiCardSkeleton />
      </div>

      {/* Detail card skeletons */}
      <div className="grid gap-4 sm:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-9 w-9 rounded-lg" />
                  <div className="space-y-1">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
                <Skeleton className="h-8 w-16" />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-2.5 w-full rounded-full" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Skeleton className="h-16 rounded-lg" />
                <Skeleton className="h-16 rounded-lg" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Upsell banner skeleton */}
      <Skeleton className="h-14 w-full rounded-lg" />

      {/* Table skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-3 w-56 mt-1" />
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))]">
                  {[1, 2, 3, 4].map((i) => (
                    <th key={i} className="px-4 py-3">
                      <Skeleton className="h-3 w-20" />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <TenantTable tenants={[]} isLoading />
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminAddonsPage() {
  const { data, isLoading, isError, refetch } = useAddonUsage();

  // Derive per-add-on revenue from total — split proportionally by price ratio
  // (Voice $10, Radiograph $20 → 1:2 ratio). Falls back gracefully if no adopters.
  const metrics: AddonMetrics | undefined = data?.metrics;
  const tenants: AddonTenantUsage[] = data?.tenants ?? [];

  function handleRefetch() {
    void refetch().then(() => {
      toast.success("Datos de add-ons actualizados.");
    });
  }

  // ── Derive per-add-on revenue ──────────────────────────────────────────────
  // Voice: $10/doc/mo, Radiograph: $20/doc/mo
  // We approximate MRR per add-on using adoption counts × unit price.
  // This is display-only; the backend total is authoritative.
  const voiceRevenueCents = metrics
    ? metrics.voice_adoption_count * 1000
    : 0;
  const radiographRevenueCents = metrics
    ? metrics.radiograph_adoption_count * 2000
    : 0;

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Uso de Add-ons
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Adopcion y revenue de AI Voice y AI Radiografia.
            </p>
          </div>
        </div>
        <AddonsLoadingSkeleton />
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (isError || !metrics) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Uso de Add-ons</h1>
        </div>
        <Card className="border-destructive/40">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertTriangle
                className="h-5 w-5 text-destructive mt-0.5 shrink-0"
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-medium text-foreground">
                  No se pudieron cargar los datos de add-ons
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Verifica tu conexion con la API o contacta al equipo de
                  infraestructura si el problema persiste.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={handleRefetch}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
                  Reintentar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Happy path ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Uso de Add-ons</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Adopcion, ingresos y oportunidades de upsell para AI Voice y AI
            Radiografia. Datos con un retraso maximo de 5 minutos.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefetch}
          disabled={isLoading}
          aria-label="Actualizar datos de add-ons"
        >
          <RefreshCw
            className={cn(
              "h-3.5 w-3.5 mr-1.5",
              isLoading && "animate-spin",
            )}
            aria-hidden="true"
          />
          Actualizar
        </Button>
      </div>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Clinicas elegibles"
          value={metrics.total_eligible_tenants}
          subtitle="Con plan compatible para add-ons"
          icon={Users}
          iconClassName="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
        />

        <KpiCard
          title="AI Voice — adopcion"
          value={
            <span>
              {metrics.voice_adoption_count}
              <span className="ml-2 text-lg font-medium text-muted-foreground">
                ({formatPercent(metrics.voice_adoption_pct)})
              </span>
            </span>
          }
          subtitle="Clinicas con AI Voice activo"
          icon={Mic}
          iconClassName="bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400"
          valueClassName="text-indigo-700 dark:text-indigo-300"
        />

        <KpiCard
          title="AI Radiografia — adopcion"
          value={
            <span>
              {metrics.radiograph_adoption_count}
              <span className="ml-2 text-lg font-medium text-muted-foreground">
                ({formatPercent(metrics.radiograph_adoption_pct)})
              </span>
            </span>
          }
          subtitle="Clinicas con AI Radiografia activo"
          icon={ScanLine}
          iconClassName="bg-violet-100 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400"
          valueClassName="text-violet-700 dark:text-violet-300"
        />

        <KpiCard
          title="Ingresos por add-ons"
          value={formatUSD(metrics.total_addon_revenue_cents)}
          subtitle="Revenue total de add-ons (MRR)"
          icon={DollarSign}
          iconClassName="bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
          valueClassName="text-green-700 dark:text-green-400"
        />
      </div>

      {/* ── Add-on Detail Cards ── */}
      <div className="grid gap-4 sm:grid-cols-2">
        <AddonDetailCard
          title="AI Voice"
          price="$10 / doctor / mes"
          adoptionPct={metrics.voice_adoption_pct}
          adoptionCount={metrics.voice_adoption_count}
          totalEligible={metrics.total_eligible_tenants}
          revenueCents={voiceRevenueCents}
          icon={Mic}
          accentClassName="bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400"
          barFillClassName="bg-indigo-500"
        />

        <AddonDetailCard
          title="AI Radiografia"
          price="$20 / doctor / mes"
          adoptionPct={metrics.radiograph_adoption_pct}
          adoptionCount={metrics.radiograph_adoption_count}
          totalEligible={metrics.total_eligible_tenants}
          revenueCents={radiographRevenueCents}
          icon={ScanLine}
          accentClassName="bg-violet-100 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400"
          barFillClassName="bg-violet-500"
        />
      </div>

      {/* ── Upsell Candidates Banner ── */}
      <UpsellBanner count={metrics.upsell_candidates} />

      {/* ── Tenant Table ── */}
      <Card className="overflow-hidden">
        <CardHeader className="pb-0">
          <CardTitle className="text-base font-semibold">
            Detalle por clinica
          </CardTitle>
          <CardDescription>
            {tenants.length} {tenants.length === 1 ? "clinica elegible" : "clinicas elegibles"} —
            estado de cada add-on por clinica
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0 mt-4">
          <TenantTable tenants={tenants} isLoading={false} />
        </CardContent>
      </Card>
    </div>
  );
}
