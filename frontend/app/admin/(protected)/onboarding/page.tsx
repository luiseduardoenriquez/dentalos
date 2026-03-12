"use client";

/**
 * Admin onboarding funnel page (SA-G03).
 *
 * Features:
 * - Header with total tenant count.
 * - Vertical funnel visualization: 7 steps from Registro to Completado,
 *   each rendered as a horizontal progress bar with count + percentage.
 *   Color gradient from indigo-600 (step 0) to emerald-500 (step 6).
 * - Stuck tenants table: clinics blocked at steps 0–3 for more than 7 days,
 *   sorted by step ascending then days_since_signup descending.
 *   Step badges: red (step 0), orange (step 1), yellow (step 2–3).
 * - Loading skeletons for both sections.
 * - Error card with retry button.
 */

import * as React from "react";
import {
  Footprints,
  AlertTriangle,
  Mail,
  TrendingDown,
  RefreshCw,
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
  useOnboardingFunnel,
  type OnboardingStepMetric,
  type OnboardingFunnelResponse,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Step color map ────────────────────────────────────────────────────────────
// Gradient from indigo-600 (step 0) to emerald-500 (step 6).

const STEP_BAR_COLORS: Record<number, string> = {
  0: "bg-indigo-600",
  1: "bg-indigo-500",
  2: "bg-violet-500",
  3: "bg-purple-500",
  4: "bg-teal-500",
  5: "bg-green-500",
  6: "bg-emerald-500",
};

function stepBarColor(step: number): string {
  return STEP_BAR_COLORS[step] ?? "bg-indigo-600";
}

// ─── Stuck-tenant step badge colors ───────────────────────────────────────────

function stuckStepBadgeClass(step: number): string {
  if (step === 0) {
    return "bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/40";
  }
  if (step === 1) {
    return "bg-orange-50 text-orange-700 border border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700/40";
  }
  // steps 2–3
  return "bg-yellow-50 text-yellow-700 border border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700/40";
}

// ─── Step label lookup ────────────────────────────────────────────────────────

const STEP_LABELS: Record<number, string> = {
  0: "Registro",
  1: "Configuracion basica",
  2: "Primer doctor",
  3: "Primer paciente",
  4: "Primera cita",
  5: "Primera factura",
  6: "Completado",
};

function stepLabel(step: number): string {
  return STEP_LABELS[step] ?? `Paso ${step}`;
}

// ─── Number formatter ─────────────────────────────────────────────────────────

function formatNumber(value: number): string {
  return value.toLocaleString("es-CO");
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function FunnelLoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Funnel bars skeleton */}
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-64 mt-1" />
        </CardHeader>
        <CardContent className="space-y-5">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-5 w-5 rounded-full" />
                  <Skeleton className="h-4 w-36" />
                </div>
                <Skeleton className="h-4 w-20" />
              </div>
              <Skeleton
                className="h-6 rounded-md"
                style={{ width: `${80 - i * 8}%` }}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Stuck tenants table skeleton */}
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-52" />
          <Skeleton className="h-4 w-72 mt-1" />
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))]">
                  {["Clinica", "Email", "Paso actual", "Dias desde registro"].map(
                    (col) => (
                      <th
                        key={col}
                        className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide"
                      >
                        {col}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))]">
                {Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-36" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-44" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-5 w-28 rounded-full" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-12" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Funnel visualization ─────────────────────────────────────────────────────

interface FunnelVisualizationProps {
  steps: OnboardingStepMetric[];
  total_tenants: number;
}

function FunnelVisualization({ steps, total_tenants }: FunnelVisualizationProps) {
  if (steps.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Footprints className="h-4 w-4 text-indigo-600" aria-hidden="true" />
            Pasos del embudo
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Sin datos disponibles.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Sort steps ascending to ensure consistent order
  const sorted = [...steps].sort((a, b) => a.step - b.step);

  // Highest count for visual scaling when pct_of_total is 0
  const maxCount = sorted.reduce((m, s) => Math.max(m, s.tenant_count), 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Footprints className="h-4 w-4 text-indigo-600" aria-hidden="true" />
          Pasos del embudo
        </CardTitle>
        <CardDescription>
          {formatNumber(total_tenants)}{" "}
          {total_tenants === 1 ? "clinica registrada" : "clinicas registradas"}
          {" "}en total
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {sorted.map((step) => {
          const pct =
            step.pct_of_total > 0
              ? step.pct_of_total
              : maxCount > 0
                ? (step.tenant_count / maxCount) * 100
                : 0;
          const barColor = stepBarColor(step.step);
          const label = step.label || stepLabel(step.step);

          return (
            <div key={step.step} className="space-y-1.5">
              {/* Row header */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2.5">
                  {/* Step number chip */}
                  <span
                    className={cn(
                      "inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white shrink-0",
                      barColor,
                    )}
                    aria-hidden="true"
                  >
                    {step.step}
                  </span>
                  <span className="font-medium text-foreground leading-tight">
                    {label}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs tabular-nums">
                  <span className="font-semibold text-foreground">
                    {formatNumber(step.tenant_count)}
                  </span>
                  <span className="text-muted-foreground">
                    {step.pct_of_total > 0
                      ? `${step.pct_of_total.toFixed(1)}%`
                      : "—"}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div
                className="h-6 w-full overflow-hidden rounded-md bg-[hsl(var(--muted))]"
                role="progressbar"
                aria-valuenow={Math.round(pct)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${label}: ${step.tenant_count} clinicas`}
              >
                <div
                  className={cn(
                    "h-full rounded-md transition-all duration-500",
                    barColor,
                  )}
                  style={{ width: `${Math.max(pct, pct > 0 ? 1 : 0).toFixed(2)}%` }}
                />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ─── Stuck tenants table ───────────────────────────────────────────────────────

interface StuckTenantsTableProps {
  stuckTenants: OnboardingFunnelResponse["stuck_tenants"];
}

function StuckTenantsTable({ stuckTenants }: StuckTenantsTableProps) {
  // Sort: step ascending, then days_since_signup descending
  const sorted = [...stuckTenants].sort((a, b) => {
    if (a.step !== b.step) return a.step - b.step;
    return b.days_since_signup - a.days_since_signup;
  });

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <TrendingDown
            className="h-4 w-4 text-orange-500"
            aria-hidden="true"
          />
          Clinicas atascadas
        </CardTitle>
        <CardDescription>
          Clinicas con mas de 7 dias en los pasos 0–3 sin avanzar. Candidatas
          para contacto proactivo.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table
            className="w-full text-sm"
            aria-label="Clinicas atascadas en onboarding"
          >
            <thead>
              <tr className="border-b border-[hsl(var(--border))]">
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Clinica
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Email
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Paso actual
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Dias desde registro
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {sorted.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-12 text-center text-sm text-muted-foreground"
                  >
                    No hay clinicas atascadas en este momento.
                  </td>
                </tr>
              ) : (
                sorted.map((tenant) => (
                  <tr
                    key={tenant.tenant_id}
                    className="hover:bg-[hsl(var(--muted))] transition-colors"
                  >
                    {/* Clinic name */}
                    <td className="px-4 py-3">
                      <span className="font-medium text-foreground leading-tight">
                        {tenant.name}
                      </span>
                    </td>

                    {/* Owner email */}
                    <td className="px-4 py-3 text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <Mail
                          className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
                          aria-hidden="true"
                        />
                        <span className="truncate max-w-[180px]">
                          {tenant.owner_email}
                        </span>
                      </div>
                    </td>

                    {/* Current step badge */}
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums",
                          stuckStepBadgeClass(tenant.step),
                        )}
                      >
                        {tenant.step} — {stepLabel(tenant.step)}
                      </span>
                    </td>

                    {/* Days since signup */}
                    <td className="px-4 py-3 text-right tabular-nums">
                      <span
                        className={cn(
                          "font-semibold",
                          tenant.days_since_signup >= 30
                            ? "text-red-600 dark:text-red-400"
                            : tenant.days_since_signup >= 14
                              ? "text-orange-600 dark:text-orange-400"
                              : "text-yellow-600 dark:text-yellow-400",
                        )}
                      >
                        {tenant.days_since_signup}d
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Error card ───────────────────────────────────────────────────────────────

interface ErrorCardProps {
  onRetry: () => void;
}

function ErrorCard({ onRetry }: ErrorCardProps) {
  return (
    <Card className="border-destructive/40">
      <CardContent className="pt-6">
        <div className="flex items-start gap-3">
          <AlertTriangle
            className="h-5 w-5 text-destructive mt-0.5 shrink-0"
            aria-hidden="true"
          />
          <div>
            <p className="text-sm font-medium text-foreground">
              No se pudo cargar el embudo de onboarding
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Verifica tu conexion o contacta al equipo de infraestructura si el
              problema persiste.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={onRetry}
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Reintentar
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminOnboardingFunnelPage() {
  const { data, isLoading, isError, refetch } = useOnboardingFunnel();

  function handleRefetch() {
    refetch().then(() => {
      toast.success("Datos del embudo actualizados.");
    });
  }

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Embudo de Onboarding
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {isLoading
              ? "Cargando metricas de activacion..."
              : data
                ? `${formatNumber(data.total_tenants)} ${
                    data.total_tenants === 1
                      ? "clinica registrada"
                      : "clinicas registradas"
                  } en la plataforma`
                : "Conversion por paso desde registro hasta primera factura."}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefetch}
          disabled={isLoading}
          aria-label="Actualizar datos del embudo"
        >
          <RefreshCw
            className={cn("h-3.5 w-3.5 mr-1.5", isLoading && "animate-spin")}
            aria-hidden="true"
          />
          Actualizar
        </Button>
      </div>

      {/* ── Loading state ── */}
      {isLoading && <FunnelLoadingSkeleton />}

      {/* ── Error state ── */}
      {isError && !isLoading && <ErrorCard onRetry={handleRefetch} />}

      {/* ── Data loaded ── */}
      {!isLoading && !isError && data && (
        <>
          {/* Funnel visualization */}
          <FunnelVisualization
            steps={data.steps}
            total_tenants={data.total_tenants}
          />

          {/* Stuck tenants section */}
          {data.stuck_tenants.length > 0 ? (
            <StuckTenantsTable stuckTenants={data.stuck_tenants} />
          ) : (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
                <Badge
                  className="bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700/40 mb-1"
                >
                  Todo en orden
                </Badge>
                <p className="text-sm font-medium text-foreground">
                  No hay clinicas atascadas en este momento
                </p>
                <p className="text-xs text-muted-foreground">
                  Todas las clinicas nuevas han avanzado mas alla del paso 3 en
                  menos de 7 dias.
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
