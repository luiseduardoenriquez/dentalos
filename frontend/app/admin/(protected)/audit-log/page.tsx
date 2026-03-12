"use client";

/**
 * Admin audit log page.
 *
 * Features:
 * - Action dropdown filter: all actions or a specific action type.
 * - Date range filter: Desde (dateFrom) and Hasta (dateTo) date inputs.
 * - Export CSV button: triggers a download via useExportData("audit").
 * - Paginated table with expandable JSON detail rows.
 * - Action badges colored by action category.
 * - Loading skeleton and error state.
 * - Previous / Next pagination controls.
 */

import { useState } from "react";
import { Shield, Download, ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAdminAuditLog,
  useExportData,
  type AuditLogEntry,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Constants ─────────────────────────────────────────────────────────────────

const ACTION_OPTIONS: { value: string; label: string }[] = [
  { value: "login", label: "login" },
  { value: "impersonate", label: "impersonate" },
  { value: "create_tenant", label: "create_tenant" },
  { value: "update_tenant", label: "update_tenant" },
  { value: "suspend_tenant", label: "suspend_tenant" },
  { value: "unsuspend_tenant", label: "unsuspend_tenant" },
  { value: "update_plan", label: "update_plan" },
  { value: "create_flag", label: "create_flag" },
  { value: "update_flag", label: "update_flag" },
  { value: "create_superadmin", label: "create_superadmin" },
  { value: "update_superadmin", label: "update_superadmin" },
  { value: "delete_superadmin", label: "delete_superadmin" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Format an ISO timestamp to DD/MM/YYYY HH:mm in es-419 locale.
 */
function formatTimestamp(iso: string): string {
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/**
 * Truncate a UUID to first 8 chars followed by ellipsis.
 */
function truncateUUID(id: string | null): string {
  if (!id) return "—";
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

// ─── Action Badge ──────────────────────────────────────────────────────────────

/**
 * Determine the Tailwind classes for a given action string.
 *
 * Color mapping:
 *  login        → blue
 *  impersonate  → amber
 *  create_*     → green
 *  update_*     → sky
 *  suspend_*    → red
 *  unsuspend_*  → emerald
 *  delete_*     → rose
 */
function getActionBadgeClasses(action: string): string {
  if (action === "login") {
    return "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300";
  }
  if (action === "impersonate") {
    return "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300";
  }
  if (action.startsWith("create_")) {
    return "border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300";
  }
  if (action.startsWith("update_")) {
    return "border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-700 dark:bg-sky-950 dark:text-sky-300";
  }
  if (action.startsWith("suspend_")) {
    return "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300";
  }
  if (action.startsWith("unsuspend_")) {
    return "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-300";
  }
  if (action.startsWith("delete_")) {
    return "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-700 dark:bg-rose-950 dark:text-rose-300";
  }
  // Fallback
  return "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300";
}

function ActionBadge({ action }: { action: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-xs font-medium",
        getActionBadgeClasses(action),
      )}
    >
      {action}
    </span>
  );
}

// ─── Table ─────────────────────────────────────────────────────────────────────

interface AuditLogTableProps {
  entries: AuditLogEntry[];
  isLoading: boolean;
  pageSize: number;
}

/**
 * Single expandable audit row.
 * Clicking "Ver" in the Detalles column toggles an inline JSON viewer below the row.
 */
function AuditLogRow({ entry }: { entry: AuditLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails =
    entry.details !== null &&
    entry.details !== undefined &&
    Object.keys(entry.details).length > 0;

  return (
    <>
      <tr className="hover:bg-[hsl(var(--muted))] transition-colors">
        {/* Fecha */}
        <td className="px-4 py-3 whitespace-nowrap text-sm text-muted-foreground tabular-nums">
          {formatTimestamp(entry.created_at)}
        </td>

        {/* Admin email */}
        <td className="px-4 py-3 text-sm text-foreground">
          {entry.admin_email ?? (
            <span className="text-muted-foreground italic">—</span>
          )}
        </td>

        {/* Action badge */}
        <td className="px-4 py-3">
          <ActionBadge action={entry.action} />
        </td>

        {/* Resource type */}
        <td className="px-4 py-3 text-sm text-muted-foreground">
          {entry.resource_type ?? "—"}
        </td>

        {/* Resource ID (truncated UUID) */}
        <td className="px-4 py-3">
          {entry.resource_id ? (
            <code
              className="text-xs font-mono text-muted-foreground bg-[hsl(var(--muted))] px-1.5 py-0.5 rounded"
              title={entry.resource_id}
            >
              {truncateUUID(entry.resource_id)}
            </code>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </td>

        {/* IP address */}
        <td className="px-4 py-3 text-sm font-mono text-muted-foreground">
          {entry.ip_address ?? "—"}
        </td>

        {/* Detalles — expandable JSON */}
        <td className="px-4 py-3">
          {hasDetails ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs gap-1"
              onClick={() => setExpanded((prev) => !prev)}
              aria-expanded={expanded}
              aria-label={expanded ? "Ocultar detalles" : "Ver detalles"}
            >
              {expanded ? (
                <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              Ver
            </Button>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </td>
      </tr>

      {/* Expanded JSON viewer */}
      {expanded && hasDetails && (
        <tr className="bg-[hsl(var(--muted)/0.4)]">
          <td colSpan={7} className="px-6 pb-4 pt-2">
            <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Detalles del evento
              </p>
              <pre className="overflow-x-auto whitespace-pre-wrap text-xs font-mono text-foreground leading-relaxed">
                {JSON.stringify(entry.details, null, 2)}
              </pre>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/**
 * Skeleton rows shown during the initial load.
 */
function AuditLogSkeletonRows({ count }: { count: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <tr key={i}>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-32" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-40" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-5 w-28 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-20" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-20" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-24" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-7 w-12 rounded" />
          </td>
        </tr>
      ))}
    </>
  );
}

function AuditLogTable({ entries, isLoading, pageSize }: AuditLogTableProps) {
  const skeletonCount = pageSize > 20 ? 20 : pageSize;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" aria-label="Registro de auditoria">
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Fecha
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Admin
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Accion
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Recurso
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              ID Recurso
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              IP
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Detalles
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {isLoading ? (
            <AuditLogSkeletonRows count={skeletonCount} />
          ) : (
            entries.map((entry) => (
              <AuditLogRow key={entry.id} entry={entry} />
            ))
          )}
        </tbody>
      </table>

      {!isLoading && entries.length === 0 && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          No se encontraron registros con los filtros actuales.
        </p>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Admin audit log page.
 *
 * State:
 * - page: current page number (resets to 1 on filter change).
 * - pageSize: items per page (10 / 20 / 50).
 * - actionFilter: "all" or a specific action string.
 * - dateFrom: ISO date string (YYYY-MM-DD) or empty.
 * - dateTo: ISO date string (YYYY-MM-DD) or empty.
 */
export default function AdminAuditLogPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<10 | 20 | 50>(20);
  const [actionFilter, setActionFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { mutate: exportData, isPending: isExporting } = useExportData();

  const { data, isLoading, isError, refetch } = useAdminAuditLog({
    page,
    pageSize,
    action: actionFilter !== "all" ? actionFilter : undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleActionChange(value: string) {
    setActionFilter(value);
    setPage(1);
  }

  function handleDateFromChange(e: React.ChangeEvent<HTMLInputElement>) {
    setDateFrom(e.target.value);
    setPage(1);
  }

  function handleDateToChange(e: React.ChangeEvent<HTMLInputElement>) {
    setDateTo(e.target.value);
    setPage(1);
  }

  function handlePageSizeChange(value: string) {
    setPageSize(Number(value) as 10 | 20 | 50);
    setPage(1);
  }

  function handleExport() {
    exportData("audit", {
      onSuccess: (blob) => {
        // Trigger browser download
        if (blob instanceof Blob) {
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `auditoria_${new Date().toISOString().slice(0, 10)}.csv`;
          document.body.appendChild(anchor);
          anchor.click();
          document.body.removeChild(anchor);
          URL.revokeObjectURL(url);
        }
        toast.success("Exportacion completada.");
      },
      onError: () => {
        toast.error("No se pudo exportar el registro. Intentalo de nuevo.");
      },
    });
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* ── Page title ── */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Shield
            className="h-7 w-7 text-muted-foreground shrink-0"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Registro de Auditoria
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {data
                ? `${data.total} ${data.total === 1 ? "evento" : "eventos"} en total`
                : "Historial de acciones realizadas por administradores"}
            </p>
          </div>
        </div>

        {/* Export CSV */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={isExporting}
          className="shrink-0 gap-1.5"
        >
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          {isExporting ? "Exportando..." : "Exportar CSV"}
        </Button>
      </div>

      {/* ── Filter bar ── */}
      <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
        {/* Action filter */}
        <Select value={actionFilter} onValueChange={handleActionChange}>
          <SelectTrigger
            className="w-full sm:w-52"
            aria-label="Filtrar por accion"
          >
            <SelectValue placeholder="Todas las acciones" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las acciones</SelectItem>
            {ACTION_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Date from */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="audit-date-from"
            className="text-sm text-muted-foreground whitespace-nowrap"
          >
            Desde
          </label>
          <input
            id="audit-date-from"
            type="date"
            value={dateFrom}
            onChange={handleDateFromChange}
            className={cn(
              "rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
              "px-3 py-2 text-sm text-foreground shadow-sm",
              "focus:outline-none focus:ring-2 focus:ring-primary-600",
            )}
            aria-label="Fecha desde"
          />
        </div>

        {/* Date to */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="audit-date-to"
            className="text-sm text-muted-foreground whitespace-nowrap"
          >
            Hasta
          </label>
          <input
            id="audit-date-to"
            type="date"
            value={dateTo}
            onChange={handleDateToChange}
            className={cn(
              "rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
              "px-3 py-2 text-sm text-foreground shadow-sm",
              "focus:outline-none focus:ring-2 focus:ring-primary-600",
            )}
            aria-label="Fecha hasta"
          />
        </div>

        {/* Page size */}
        <Select value={String(pageSize)} onValueChange={handlePageSizeChange}>
          <SelectTrigger
            className="w-full sm:w-28"
            aria-label="Elementos por pagina"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="10">10 / pag.</SelectItem>
            <SelectItem value="20">20 / pag.</SelectItem>
            <SelectItem value="50">50 / pag.</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ── Error state ── */}
      {isError && (
        <Card className="border-destructive-200 dark:border-destructive-700/40">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive-600 dark:text-destructive-400">
              No se pudo cargar el registro de auditoria.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => refetch()}
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Table ── */}
      {!isError && (
        <Card className="overflow-hidden">
          <AuditLogTable
            entries={data?.items ?? []}
            isLoading={isLoading}
            pageSize={pageSize}
          />
        </Card>
      )}

      {/* ── Pagination ── */}
      {!isError && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Pagina {page} de {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || isLoading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || isLoading}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
