"use client";

/**
 * Admin data retention page.
 *
 * Displays:
 * - Retention policies per data type with days-to-years formatting,
 *   oldest record date, and amber badge when records are eligible for archival.
 * - Archivable tenants table: cancelled clinics older than 1 year,
 *   with red highlight for tenants cancelled more than 2 years ago.
 *
 * All UI text in Spanish (es-419). HABEAS DATA compliance view.
 */

import { Archive, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useDataRetention,
  type RetentionPolicyItem,
  type ArchivableTenantItem,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

// ─── Constants ─────────────────────────────────────────────────────────────────

/**
 * Human-readable Spanish labels for each data_type value returned by the API.
 */
const DATA_TYPE_LABELS: Record<string, string> = {
  clinical_records: "Historias Clínicas",
  audit_logs: "Registros de Auditoría",
  notifications: "Notificaciones",
  consent_records: "Consentimientos",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Convert a retention_days integer to a human-readable Spanish string.
 *
 * Examples:
 *   3650 → "10 años"
 *   365  → "1 año"
 *   730  → "2 años"
 *   180  → "180 días"
 */
function formatRetentionDays(days: number): string {
  if (days >= 365 && days % 365 === 0) {
    const years = days / 365;
    return `${years} ${years === 1 ? "año" : "años"}`;
  }
  return `${days} días`;
}

/**
 * Format an ISO timestamp to DD/MM/YYYY using es-419 locale.
 * Returns "—" if the value is null or invalid.
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
    return iso;
  }
}

/**
 * Return the Spanish label for a data_type value.
 * Falls back to the raw value if not mapped.
 */
function getDataTypeLabel(dataType: string): string {
  return DATA_TYPE_LABELS[dataType] ?? dataType;
}

// ─── Policy Card ──────────────────────────────────────────────────────────────

/**
 * Displays a single retention policy.
 *
 * Amber badge on records_eligible indicates that records are pending archival.
 */
function PolicyCard({ policy }: { policy: RetentionPolicyItem }) {
  const label = getDataTypeLabel(policy.data_type);
  const retentionLabel = formatRetentionDays(policy.retention_days);
  const hasEligible = policy.records_eligible > 0;

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5 space-y-3">
      {/* Header row: label + eligible badge */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-foreground leading-snug">
          {label}
        </p>
        {hasEligible && (
          <span
            className={cn(
              "inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
              "border-amber-300 bg-amber-50 text-amber-700",
              "dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300",
            )}
            aria-label={`${policy.records_eligible} registros elegibles para archivado`}
          >
            {policy.records_eligible.toLocaleString("es-419")} elegibles
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-xs text-muted-foreground leading-relaxed">
        {policy.description}
      </p>

      {/* Retention period */}
      <div className="flex items-center gap-2">
        <Clock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="text-xs text-muted-foreground">
          Retención:{" "}
          <span className="font-medium text-foreground">{retentionLabel}</span>
        </span>
      </div>

      {/* Oldest record */}
      <div className="text-xs text-muted-foreground">
        Registro más antiguo:{" "}
        <span className="font-medium text-foreground">
          {formatDate(policy.current_oldest)}
        </span>
      </div>
    </div>
  );
}

// ─── Policy Section ───────────────────────────────────────────────────────────

function PolicySkeletonCard() {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
      <Skeleton className="h-3 w-28" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}

interface PoliciesSectionProps {
  policies: RetentionPolicyItem[];
  isLoading: boolean;
}

function PoliciesSection({ policies, isLoading }: PoliciesSectionProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-foreground">
        Políticas de Retención
      </h2>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <PolicySkeletonCard key={i} />
            ))
          : policies.map((policy) => (
              <PolicyCard key={policy.data_type} policy={policy} />
            ))}
      </div>
    </div>
  );
}

// ─── Archivable Tenants Table ─────────────────────────────────────────────────

function ArchivableTenantsSkeletonRows({ count }: { count: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <tr key={i}>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-40" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-5 w-24 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-28" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-16" />
          </td>
        </tr>
      ))}
    </>
  );
}

interface ArchivableTenantRowProps {
  tenant: ArchivableTenantItem;
}

function ArchivableTenantRow({ tenant }: ArchivableTenantRowProps) {
  const isLongOverdue = tenant.days_since_cancelled > 730;

  return (
    <tr className="hover:bg-[hsl(var(--muted))] transition-colors">
      {/* Clínica */}
      <td className="px-4 py-3 text-sm font-medium text-foreground">
        {tenant.tenant_name}
      </td>

      {/* Estado */}
      <td className="px-4 py-3">
        <span
          className={cn(
            "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
            "border-slate-300 bg-slate-50 text-slate-700",
            "dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300",
          )}
        >
          {tenant.status}
        </span>
      </td>

      {/* Cancelada el */}
      <td className="px-4 py-3 text-sm text-muted-foreground tabular-nums">
        {formatDate(tenant.cancelled_at)}
      </td>

      {/* Días desde cancelación */}
      <td
        className={cn(
          "px-4 py-3 text-sm tabular-nums font-medium",
          isLongOverdue
            ? "text-red-600 dark:text-red-400"
            : "text-muted-foreground",
        )}
        aria-label={`${tenant.days_since_cancelled} días desde cancelación${isLongOverdue ? " — más de 2 años" : ""}`}
      >
        {tenant.days_since_cancelled.toLocaleString("es-419")}
        {isLongOverdue && (
          <span className="ml-1 text-xs font-normal text-red-500 dark:text-red-400">
            (+2 años)
          </span>
        )}
      </td>
    </tr>
  );
}

interface ArchivableTenantsSectionProps {
  tenants: ArchivableTenantItem[];
  totalArchivable: number;
  isLoading: boolean;
}

function ArchivableTenantsSection({
  tenants,
  totalArchivable,
  isLoading,
}: ArchivableTenantsSectionProps) {
  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold text-foreground">
          Clínicas Archivables
        </h2>
        {!isLoading && (
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
              totalArchivable > 0
                ? "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300"
                : "border-slate-300 bg-slate-50 text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400",
            )}
          >
            {totalArchivable}
          </span>
        )}
        {isLoading && <Skeleton className="h-5 w-8 rounded-full" />}
      </div>

      <p className="text-xs text-muted-foreground">
        Clínicas canceladas hace más de 1 año
      </p>

      {/* Table card */}
      <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
        <div className="overflow-x-auto">
          <table
            className="w-full text-sm"
            aria-label="Clínicas archivables"
          >
            <thead>
              <tr className="border-b border-[hsl(var(--border))]">
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Clínica
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Estado
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
                  Cancelada el
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
                  Días desde cancelación
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {isLoading ? (
                <ArchivableTenantsSkeletonRows count={4} />
              ) : tenants.length > 0 ? (
                tenants.map((tenant) => (
                  <ArchivableTenantRow key={tenant.tenant_id} tenant={tenant} />
                ))
              ) : (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-10 text-center text-sm text-muted-foreground"
                  >
                    No hay clínicas pendientes de archivado
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Data retention management page for the DentalOS superadmin portal.
 *
 * Shows HABEAS DATA compliance context:
 * - Retention policies per data type (clinical records, audit logs, etc.)
 * - List of cancelled tenants whose data is eligible for archival
 */
export default function DataRetentionPage() {
  const { data, isLoading, isError, refetch } =
    useDataRetention();

  const policies: RetentionPolicyItem[] = data?.policies ?? [];
  const archivableTenants: ArchivableTenantItem[] =
    data?.archivable_tenants ?? [];
  const totalArchivable: number = data?.total_archivable ?? 0;

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start gap-3">
        <Archive
          className="h-7 w-7 text-muted-foreground shrink-0 mt-0.5"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Retención de Datos
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Políticas de retención y datos archivables — HABEAS DATA
          </p>
        </div>
      </div>

      {/* ── Error state ── */}
      {isError && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-destructive">
              No se pudo cargar la información de retención
            </CardTitle>
          </CardHeader>
          <CardContent>
            <button
              type="button"
              onClick={() => refetch()}
              className={cn(
                "rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
                "px-3 py-1.5 text-sm font-medium text-foreground shadow-sm",
                "hover:bg-[hsl(var(--muted))] transition-colors",
              )}
            >
              Reintentar
            </button>
          </CardContent>
        </Card>
      )}

      {/* ── Policies section ── */}
      {!isError && (
        <PoliciesSection policies={policies} isLoading={isLoading} />
      )}

      {/* ── Archivable tenants section ── */}
      {!isError && (
        <ArchivableTenantsSection
          tenants={archivableTenants}
          totalArchivable={totalArchivable}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}
