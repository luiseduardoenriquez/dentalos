"use client";

/**
 * Admin tenants list page.
 *
 * Features:
 * - Free-text search with 300ms debounce.
 * - Status dropdown filter: Todos / active / trial / suspended / cancelled.
 * - Page size selector: 10 / 20 / 50.
 * - Paginated table with links to each tenant's detail page.
 * - Previous / Next pagination controls.
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAdminTenants, type TenantSummary } from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ─── Plan Badge ───────────────────────────────────────────────────────────────

const PLAN_CLASSES: Record<string, string> = {
  free: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  starter:
    "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700/40",
  pro: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-700/40",
  clinica:
    "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-700/40",
  enterprise:
    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700/40",
};

function PlanBadge({ plan }: { plan: string }) {
  const normalized = plan.toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border",
        PLAN_CLASSES[normalized] ?? PLAN_CLASSES.free,
      )}
    >
      {plan}
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

// ─── Table ────────────────────────────────────────────────────────────────────

interface TenantsTableProps {
  tenants: TenantSummary[];
  isLoading: boolean;
  pageSize: number;
}

function TenantsTable({ tenants, isLoading, pageSize }: TenantsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" aria-label="Lista de clinicas">
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Nombre
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Slug
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Plan
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Estado
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Usuarios
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Creado
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {isLoading
            ? Array.from({ length: pageSize > 10 ? 10 : pageSize }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-40" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-28" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-20 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-8 ml-auto" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-24" />
                  </td>
                </tr>
              ))
            : tenants.map((tenant) => (
                <tr
                  key={tenant.id}
                  className="hover:bg-[hsl(var(--muted))] transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-foreground">
                    <Link
                      href={`/admin/tenants/${tenant.id}`}
                      className="hover:underline text-primary-600 dark:text-primary-400"
                    >
                      {tenant.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs font-mono text-muted-foreground bg-[hsl(var(--muted))] px-1.5 py-0.5 rounded">
                      {tenant.slug}
                    </code>
                  </td>
                  <td className="px-4 py-3">
                    <PlanBadge plan={tenant.plan_name} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={tenant.status} />
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-foreground">
                    {tenant.user_count}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                    {formatDate(tenant.created_at)}
                  </td>
                </tr>
              ))}
        </tbody>
      </table>

      {!isLoading && tenants.length === 0 && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          No se encontraron clinicas con los filtros actuales.
        </p>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Admin tenants list.
 *
 * State is managed locally (no URL params for MVP):
 * - page: current page number (resets to 1 on filter change).
 * - pageSize: items per page, from 10/20/50 selector.
 * - searchInput: raw input string (not debounced).
 * - debouncedSearch: debounced version passed to the hook (300ms).
 * - statusFilter: "all" or a specific status string.
 */
export default function AdminTenantsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<10 | 20 | 50>(20);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Debounce the search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      // Reset to page 1 when search changes
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Reset page when status changes
  function handleStatusChange(value: string) {
    setStatusFilter(value);
    setPage(1);
  }

  // Reset page when page size changes
  function handlePageSizeChange(value: string) {
    setPageSize(Number(value) as 10 | 20 | 50);
    setPage(1);
  }

  const { data, isLoading, isError, refetch } = useAdminTenants({
    page,
    page_size: pageSize,
    search: debouncedSearch || undefined,
    status: statusFilter !== "all" ? statusFilter : undefined,
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-6">
      {/* ── Page title ── */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Clinicas</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {data ? `${data.total} clinicas en total` : "Listado de todas las clinicas de la plataforma"}
        </p>
      </div>

      {/* ── Filters ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
            aria-hidden="true"
          />
          <Input
            type="search"
            placeholder="Buscar por nombre o slug..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
            aria-label="Buscar clinicas"
          />
        </div>

        {/* Status filter */}
        <Select value={statusFilter} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-full sm:w-44" aria-label="Filtrar por estado">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="active">Activa</SelectItem>
            <SelectItem value="trial">Trial</SelectItem>
            <SelectItem value="suspended">Suspendida</SelectItem>
            <SelectItem value="cancelled">Cancelada</SelectItem>
          </SelectContent>
        </Select>

        {/* Page size */}
        <Select value={String(pageSize)} onValueChange={handlePageSizeChange}>
          <SelectTrigger className="w-full sm:w-28" aria-label="Elementos por pagina">
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
              No se pudo cargar la lista de clinicas.
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
          <TenantsTable
            tenants={data?.items ?? []}
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
