"use client";

/**
 * Admin compliance dashboard page — Resolución 1888 (Colombia).
 *
 * Sections:
 * 1. Four KPI cards: RIPS, RDA, Consent templates, RETHUS verification rates.
 * 2. Tenant-by-tenant compliance table with status badges and last-submission
 *    dates for each regulatory requirement.
 *
 * Data source: useComplianceDashboard → GET /admin/compliance
 *
 * Color thresholds applied consistently across KPIs:
 *   >80% → green  |  >50% → amber  |  ≤50% → red
 */

import { FileCheck2, ClipboardList, ShieldCheck, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useComplianceDashboard,
  type ComplianceKPIs,
  type TenantComplianceItem,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

// ─── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Format an ISO timestamp to DD/MM/YYYY in the es-419 locale.
 * Returns "—" when the value is null or invalid.
 */
function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return "—";
  }
}

/**
 * Derive Tailwind color classes for a compliance percentage.
 *   >80 → green  |  >50 → amber  |  ≤50 → red
 */
function pctColorClasses(pct: number): { value: string; badge: string } {
  if (pct > 80) {
    return {
      value: "text-green-700 dark:text-green-400",
      badge:
        "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/40",
    };
  }
  if (pct > 50) {
    return {
      value: "text-amber-700 dark:text-amber-400",
      badge:
        "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700/40",
    };
  }
  return {
    value: "text-red-700 dark:text-red-400",
    badge:
      "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/40",
  };
}

// ─── KPI Card ──────────────────────────────────────────────────────────────────

interface ComplianceKpiCardProps {
  title: string;
  /** Primary numeric value to display large (e.g. "12 / 15" or "80.0%"). */
  primaryValue: string;
  /** Percentage shown as a small colored pill below the primary value. */
  pct: number;
  /** Label describing what the percentage represents. */
  pctLabel: string;
  icon: React.ElementType;
  isLoading?: boolean;
}

function ComplianceKpiCard({
  title,
  primaryValue,
  pct,
  pctLabel,
  icon: Icon,
  isLoading,
}: ComplianceKpiCardProps) {
  const colors = pctColorClasses(pct);

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
          {title}
        </p>
        <div
          className="flex items-center justify-center w-9 h-9 rounded-lg shrink-0 bg-[hsl(var(--muted))]"
          aria-hidden="true"
        >
          <Icon className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
        </div>
      </div>

      {isLoading ? (
        <>
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </>
      ) : (
        <>
          <p className={cn("text-3xl font-bold tabular-nums tracking-tight", colors.value)}>
            {primaryValue}
          </p>
          <span
            className={cn(
              "self-start inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border",
              colors.badge,
            )}
          >
            {pct.toFixed(1)}% {pctLabel}
          </span>
        </>
      )}
    </div>
  );
}

// ─── KPI Grid ──────────────────────────────────────────────────────────────────

function ComplianceKpiGrid({
  kpis,
  isLoading,
}: {
  kpis: ComplianceKPIs | undefined;
  isLoading: boolean;
}) {
  const total = kpis?.total_colombian_tenants ?? 0;

  return (
    <section aria-label="Indicadores clave de cumplimiento">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <ComplianceKpiCard
          title="RIPS al dia"
          primaryValue={isLoading ? "—" : `${kpis!.rips_compliant} / ${total}`}
          pct={kpis?.rips_compliant_pct ?? 0}
          pctLabel="al dia"
          icon={FileCheck2}
          isLoading={isLoading}
        />
        <ComplianceKpiCard
          title="RDA al dia"
          primaryValue={isLoading ? "—" : `${kpis!.rda_compliant} / ${total}`}
          pct={kpis?.rda_compliant_pct ?? 0}
          pctLabel="al dia"
          icon={ClipboardList}
          isLoading={isLoading}
        />
        <ComplianceKpiCard
          title="Plantillas de Consentimiento"
          primaryValue={
            isLoading ? "—" : `${kpis!.consent_compliant} / ${total}`
          }
          pct={kpis?.consent_compliant_pct ?? 0}
          pctLabel="completas"
          icon={ShieldCheck}
          isLoading={isLoading}
        />
        <ComplianceKpiCard
          title="RETHUS Verificado"
          primaryValue={
            isLoading ? "—" : `${kpis!.rethus_verified_pct.toFixed(1)}%`
          }
          pct={kpis?.rethus_verified_pct ?? 0}
          pctLabel="verificados"
          icon={UserCheck}
          isLoading={isLoading}
        />
      </div>
    </section>
  );
}

// ─── Status Badges ─────────────────────────────────────────────────────────────

/**
 * Badge for rips_status / rda_status fields.
 *   up_to_date → green "Al dia"
 *   overdue    → red   "Vencido"
 *   never      → gray  "Nunca"
 */
function SubmissionStatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    { label: string; className: string }
  > = {
    up_to_date: {
      label: "Al dia",
      className:
        "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/40",
    },
    overdue: {
      label: "Vencido",
      className:
        "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/40",
    },
    never: {
      label: "Nunca",
      className:
        "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
    },
  };

  const { label, className } = config[status] ?? config.never;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border",
        className,
      )}
    >
      {label}
    </span>
  );
}

// ─── Table Skeleton ────────────────────────────────────────────────────────────

function TableLoadingSkeleton() {
  return (
    <tbody className="divide-y divide-[hsl(var(--border))]">
      {Array.from({ length: 6 }).map((_, i) => (
        <tr key={i}>
          {/* Clinica */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-40" />
          </td>
          {/* RIPS */}
          <td className="px-5 py-3">
            <Skeleton className="h-5 w-16 rounded-full" />
          </td>
          {/* RDA */}
          <td className="px-5 py-3">
            <Skeleton className="h-5 w-16 rounded-full" />
          </td>
          {/* Consentimientos */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-12" />
          </td>
          {/* Doctores verificados */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-14" />
          </td>
          {/* Ultimo RIPS */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-20" />
          </td>
          {/* Ultimo RDA */}
          <td className="px-5 py-3">
            <Skeleton className="h-4 w-20" />
          </td>
        </tr>
      ))}
    </tbody>
  );
}

// ─── Tenant Compliance Table ───────────────────────────────────────────────────

function TenantComplianceTable({
  tenants,
  isLoading,
}: {
  tenants: TenantComplianceItem[];
  isLoading: boolean;
}) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
      {/* Card header */}
      <div className="px-5 py-4 border-b border-[hsl(var(--border))]">
        <h2 className="text-base font-semibold text-[hsl(var(--card-foreground))]">
          Estado por clinica
        </h2>
        <p className="mt-0.5 text-sm text-[hsl(var(--muted-foreground))]">
          Cumplimiento regulatorio individual para clinicas colombianas
        </p>
      </div>

      <div className="overflow-x-auto">
        <table
          className="w-full text-sm"
          aria-label="Estado de cumplimiento por clinica"
        >
          <thead>
            <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)]">
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Clinica
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                RIPS
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                RDA
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Consentimientos
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Doctores Verificados
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Ultimo RIPS
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide whitespace-nowrap">
                Ultimo RDA
              </th>
            </tr>
          </thead>

          {isLoading ? (
            <TableLoadingSkeleton />
          ) : (
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {tenants.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-sm text-[hsl(var(--muted-foreground))]"
                  >
                    No hay clinicas colombianas registradas.
                  </td>
                </tr>
              ) : (
                tenants.map((tenant) => {
                  const consentMet =
                    tenant.consent_templates_count >=
                    tenant.consent_templates_required;
                  const allDoctorsVerified =
                    tenant.doctors_total > 0 &&
                    tenant.doctors_verified >= tenant.doctors_total;

                  return (
                    <tr
                      key={tenant.tenant_id}
                      className="hover:bg-[hsl(var(--muted)/0.3)] transition-colors"
                    >
                      {/* Clinica */}
                      <td className="px-5 py-3 font-medium text-[hsl(var(--card-foreground))] whitespace-nowrap">
                        {tenant.tenant_name}
                      </td>

                      {/* RIPS status */}
                      <td className="px-5 py-3">
                        <SubmissionStatusBadge status={tenant.rips_status} />
                      </td>

                      {/* RDA status */}
                      <td className="px-5 py-3">
                        <SubmissionStatusBadge status={tenant.rda_status} />
                      </td>

                      {/* Consent templates: count / required */}
                      <td className="px-5 py-3 tabular-nums">
                        <span
                          className={cn(
                            "font-medium",
                            consentMet
                              ? "text-green-700 dark:text-green-400"
                              : "text-red-700 dark:text-red-400",
                          )}
                        >
                          {tenant.consent_templates_count}
                        </span>
                        <span className="text-[hsl(var(--muted-foreground))]">
                          {" / "}
                          {tenant.consent_templates_required}
                        </span>
                      </td>

                      {/* Doctors: verified / total */}
                      <td className="px-5 py-3 tabular-nums">
                        <div className="flex items-center gap-1.5">
                          {allDoctorsVerified && (
                            <svg
                              className="h-3.5 w-3.5 shrink-0 text-green-600 dark:text-green-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2.5}
                              aria-hidden="true"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M4.5 12.75l6 6 9-13.5"
                              />
                            </svg>
                          )}
                          <span
                            className={cn(
                              "font-medium",
                              allDoctorsVerified
                                ? "text-green-700 dark:text-green-400"
                                : "text-[hsl(var(--card-foreground))]",
                            )}
                          >
                            {tenant.doctors_verified}
                          </span>
                          <span className="text-[hsl(var(--muted-foreground))]">
                            / {tenant.doctors_total}
                          </span>
                        </div>
                      </td>

                      {/* Last RIPS submission */}
                      <td className="px-5 py-3 text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                        {formatDate(tenant.last_rips_at)}
                      </td>

                      {/* Last RDA submission */}
                      <td className="px-5 py-3 text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                        {formatDate(tenant.last_rda_at)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          )}
        </table>
      </div>
    </div>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

/**
 * Compliance dashboard for Colombian clinics.
 *
 * Data source: useComplianceDashboard → GET /admin/compliance (stale 10 min).
 *
 * Layout:
 * 1. Page header with title + description.
 * 2. 4-column KPI cards (RIPS, RDA, Consentimientos, RETHUS).
 * 3. Full-width tenant compliance table.
 *
 * Error handling: dedicated error card with retry action so a temporary API
 * outage does not leave the page entirely blank.
 */
export default function AdminCompliancePage() {
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useComplianceDashboard();

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">
          Cumplimiento Regulatorio
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Estado de cumplimiento para clinicas colombianas — Resolucion 1888
        </p>
      </div>

      {/* ── Error state ── */}
      {isError && (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6">
          <p className="text-sm text-red-600 dark:text-red-400">
            No se pudo cargar el estado de cumplimiento. Verifica la conexion
            con la API.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => refetch()}
          >
            Reintentar
          </Button>
        </div>
      )}

      {/* ── KPI cards ── */}
      {!isError && (
        <ComplianceKpiGrid kpis={data?.kpis} isLoading={isLoading} />
      )}

      {/* ── Tenant compliance table ── */}
      {!isError && (
        <TenantComplianceTable
          tenants={data?.tenants ?? []}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}
