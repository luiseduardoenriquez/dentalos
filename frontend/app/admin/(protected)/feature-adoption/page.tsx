"use client";

/**
 * Admin feature adoption dashboard (SA-G02).
 *
 * Sections:
 * - Summary adoption bars: one bar per feature, sorted by adoption_pct desc.
 *   Bar color: green >60%, amber >30%, red otherwise.
 * - Tenant matrix table: one row per clinic, one column per feature (checkmark/dash),
 *   plus features_used / features_total in the last column.
 *   Sorted by features_used descending.
 * - Loading skeleton while fetching.
 * - Error state with retry button.
 */

import React from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useFeatureAdoption,
  type FeatureAdoptionResponse,
  type FeatureAdoptionSummary,
  type TenantFeatureUsage,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

// ─── Feature label map (Spanish) ─────────────────────────────────────────────

const FEATURE_LABELS: Record<string, string> = {
  odontogram: "Odontograma",
  appointments: "Citas",
  billing: "Facturacion",
  portal: "Portal Paciente",
  whatsapp: "WhatsApp",
  voice: "Voz IA",
  ai_reports: "Reportes IA",
  telemedicine: "Telemedicina",
};

/** Canonical feature key order used for both the bar section and the matrix columns. */
const FEATURE_KEYS: (keyof TenantFeatureUsage)[] = [
  "odontogram",
  "appointments",
  "billing",
  "portal",
  "whatsapp",
  "voice",
  "ai_reports",
  "telemedicine",
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function featureLabel(key: string): string {
  return FEATURE_LABELS[key] ?? key;
}

/** Returns a Tailwind bg class for the bar fill based on adoption percentage. */
function barFillClass(pct: number): string {
  if (pct > 60) return "bg-green-500";
  if (pct > 30) return "bg-amber-500";
  return "bg-red-500";
}

/** Returns a Tailwind text class for the percentage label based on adoption percentage. */
function barTextClass(pct: number): string {
  if (pct > 60) return "text-green-700 dark:text-green-400";
  if (pct > 30) return "text-amber-700 dark:text-amber-400";
  return "text-red-700 dark:text-red-400";
}

// ─── Summary Adoption Bars ────────────────────────────────────────────────────

interface AdoptionBarRowProps {
  item: FeatureAdoptionSummary;
  totalTenants: number;
}

function AdoptionBarRow({ item, totalTenants }: AdoptionBarRowProps) {
  const pct = Math.min(100, Math.max(0, item.adoption_pct));
  const fillCls = barFillClass(pct);
  const textCls = barTextClass(pct);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="font-medium text-[hsl(var(--foreground))] min-w-[140px]">
          {featureLabel(item.feature_name)}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums">
            {item.adoption_count} {item.adoption_count === 1 ? "clinica" : "clinicas"}
          </span>
          <span className={cn("text-xs font-semibold tabular-nums w-12 text-right", textCls)}>
            {pct.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-[hsl(var(--muted))]">
        <div
          className={cn(
            "h-2.5 rounded-full transition-all duration-500",
            fillCls,
          )}
          style={{ width: `${pct.toFixed(1)}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Adopcion de ${featureLabel(item.feature_name)}: ${pct.toFixed(0)}%`}
        />
      </div>
    </div>
  );
}

interface SummaryBarsCardProps {
  summary: FeatureAdoptionSummary[];
  totalTenants: number;
}

function SummaryBarsCard({ summary, totalTenants }: SummaryBarsCardProps) {
  // Sort by adoption_pct descending
  const sorted = [...summary].sort((a, b) => b.adoption_pct - a.adoption_pct);

  if (sorted.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Adopcion por feature
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
          Adopcion por feature
        </CardTitle>
        <CardDescription>
          Porcentaje de clinicas que usan cada modulo —{" "}
          <span className="text-green-600 dark:text-green-400 font-medium">verde</span> ={" "}
          {">"} 60%,{" "}
          <span className="text-amber-600 dark:text-amber-400 font-medium">amarillo</span>{" "}
          = {">"} 30%,{" "}
          <span className="text-red-600 dark:text-red-400 font-medium">rojo</span> = bajo
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-5">
          {sorted.map((item) => (
            <AdoptionBarRow
              key={item.feature_name}
              item={item}
              totalTenants={totalTenants}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Tenant Matrix Table ──────────────────────────────────────────────────────

interface TenantMatrixTableProps {
  tenants: TenantFeatureUsage[];
}

function TenantMatrixTable({ tenants }: TenantMatrixTableProps) {
  // Sort by features_used descending
  const sorted = [...tenants].sort((a, b) => b.features_used - a.features_used);

  return (
    <div className="overflow-x-auto">
      <table
        className="w-full text-sm"
        aria-label="Uso de features por clinica"
      >
        <thead>
          <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)]">
            <th className="px-4 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
              Clinica
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
              Plan
            </th>
            {FEATURE_KEYS.map((key) => (
              <th
                key={String(key)}
                className="px-3 py-3 text-center text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap"
              >
                {featureLabel(String(key))}
              </th>
            ))}
            <th className="px-4 py-3 text-center text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
              Total
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {sorted.map((tenant) => (
            <tr
              key={tenant.tenant_id}
              className="hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
            >
              {/* Clinic name */}
              <td className="px-4 py-3 font-medium text-[hsl(var(--foreground))] whitespace-nowrap">
                {tenant.tenant_name}
              </td>

              {/* Plan badge */}
              <td className="px-4 py-3 whitespace-nowrap">
                <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-[hsl(var(--muted))] text-[hsl(var(--foreground))] border-[hsl(var(--border))]">
                  {tenant.plan_name}
                </span>
              </td>

              {/* Feature cells */}
              {FEATURE_KEYS.map((key) => {
                const enabled = Boolean(tenant[key]);
                return (
                  <td
                    key={String(key)}
                    className="px-3 py-3 text-center"
                    aria-label={`${featureLabel(String(key))}: ${enabled ? "activo" : "inactivo"}`}
                  >
                    {enabled ? (
                      <span
                        className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-sm font-bold"
                        aria-hidden="true"
                      >
                        ✓
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center justify-center w-6 h-6 rounded-full text-[hsl(var(--muted-foreground))] text-sm"
                        aria-hidden="true"
                      >
                        —
                      </span>
                    )}
                  </td>
                );
              })}

              {/* Total column */}
              <td className="px-4 py-3 text-center whitespace-nowrap">
                <span
                  className={cn(
                    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums",
                    tenant.features_used >= tenant.features_total * 0.75
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                      : tenant.features_used >= tenant.features_total * 0.4
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
                  )}
                >
                  {tenant.features_used}/{tenant.features_total}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {sorted.length === 0 && (
        <p className="py-12 text-center text-sm text-[hsl(var(--muted-foreground))]">
          No hay clinicas con datos de adopcion disponibles.
        </p>
      )}
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function FeatureAdoptionLoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Summary bars skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-44" />
          <Skeleton className="h-3 w-72 mt-1" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-5">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-2.5 w-full rounded-full" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Matrix table skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3 w-60 mt-1" />
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))]">
                  {Array.from({ length: 11 }).map((_, i) => (
                    <th key={i} className="px-4 py-3">
                      <Skeleton className="h-3 w-16 mx-auto" />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))]">
                {Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-36" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-5 w-20 rounded-full" />
                    </td>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j} className="px-3 py-3 text-center">
                        <Skeleton className="h-6 w-6 rounded-full mx-auto" />
                      </td>
                    ))}
                    <td className="px-4 py-3 text-center">
                      <Skeleton className="h-5 w-12 rounded-full mx-auto" />
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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function FeatureAdoptionPage() {
  const { data, isLoading, isError, refetch } = useFeatureAdoption();

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Adopcion de Features
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Que features usa cada clinica
          </p>
        </div>
        <FeatureAdoptionLoadingSkeleton />
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (isError || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Adopcion de Features
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Que features usa cada clinica
          </p>
        </div>
        <Card className="border-destructive/40">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertTriangle
                className="h-5 w-5 text-destructive mt-0.5 shrink-0"
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-medium text-[hsl(var(--foreground))]">
                  No se pudieron cargar los datos de adopcion
                </p>
                <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                  Verifica tu conexion con la API o contacta al equipo de
                  infraestructura si el problema persiste.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => void refetch()}
                >
                  <RefreshCw
                    className="h-3.5 w-3.5 mr-1.5"
                    aria-hidden="true"
                  />
                  Reintentar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { summary, tenants, total_tenants } = data as FeatureAdoptionResponse;

  // ── Happy path ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Adopcion de Features
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Que features usa cada clinica
        </p>
      </div>

      {/* ── Summary adoption bars ── */}
      <SummaryBarsCard summary={summary} totalTenants={total_tenants} />

      {/* ── Tenant matrix table ── */}
      <Card className="overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
        <CardHeader className="pb-0">
          <CardTitle className="text-base font-semibold">
            Matriz de adopcion por clinica
          </CardTitle>
          <CardDescription>
            {total_tenants}{" "}
            {total_tenants === 1 ? "clinica registrada" : "clinicas registradas"}{" "}
            — ordenadas por cantidad de features activos
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0 mt-4">
          <TenantMatrixTable tenants={tenants} />
        </CardContent>
      </Card>
    </div>
  );
}
