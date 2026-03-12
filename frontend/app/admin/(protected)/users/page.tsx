"use client";

/**
 * Admin cross-tenant user search page.
 *
 * Features:
 * - Free-text search with 300ms debounce (min 2 chars to trigger).
 * - Role filter dropdown: Todos / clinic_owner / doctor / assistant / receptionist.
 * - Results table: Email, Nombre, Apellido, Rol, Clinica, Estado, Ultimo acceso, Multi-clinica.
 * - Role badges colored by role.
 * - Status badges: active=green, inactive=gray, suspended=red.
 * - Multi-clinic users get a purple "Multi-clinica" badge.
 * - Loading skeleton rows while fetching.
 * - Empty state when query is shorter than 2 chars.
 * - Previous / Next pagination controls with total count.
 */

import React, { useState } from "react";
import { Search, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  useCrossTenantUserSearch,
  type CrossTenantUserItem,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

// ─── Constants ──────────────────────────────────────────────────────────────────

const ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: "clinic_owner", label: "Propietario" },
  { value: "doctor", label: "Doctor" },
  { value: "assistant", label: "Asistente" },
  { value: "receptionist", label: "Recepcionista" },
];

const PAGE_SIZE = 20;

// ─── Helpers ────────────────────────────────────────────────────────────────────

/**
 * Format an ISO timestamp to DD/MM/YYYY HH:mm in es-419 locale.
 * Returns "—" if null or invalid.
 */
function formatLastLogin(iso: string | null): string {
  if (!iso) return "—";
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

// ─── Role Badge ─────────────────────────────────────────────────────────────────

const ROLE_BADGE_CLASSES: Record<string, string> = {
  clinic_owner:
    "border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  doctor:
    "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300",
  assistant:
    "border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300",
  receptionist:
    "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300",
};

const ROLE_LABELS: Record<string, string> = {
  clinic_owner: "Propietario",
  doctor: "Doctor",
  assistant: "Asistente",
  receptionist: "Recepcionista",
};

function RoleBadge({ role }: { role: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        ROLE_BADGE_CLASSES[role] ??
          "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300",
      )}
    >
      {ROLE_LABELS[role] ?? role}
    </span>
  );
}

// ─── Status Badge ───────────────────────────────────────────────────────────────

const STATUS_BADGE_CLASSES: Record<string, string> = {
  active:
    "border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300",
  inactive:
    "border-slate-300 bg-slate-50 text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400",
  suspended:
    "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Activo",
  inactive: "Inactivo",
  suspended: "Suspendido",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        STATUS_BADGE_CLASSES[status] ??
          "border-slate-300 bg-slate-50 text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400",
      )}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ─── Multi-Clinic Badge ──────────────────────────────────────────────────────────

function MultiClinicBadge() {
  return (
    <span className="inline-flex items-center rounded-full border border-purple-300 bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700 dark:border-purple-700 dark:bg-purple-950 dark:text-purple-300">
      Multi-clinica
    </span>
  );
}

// ─── Table ──────────────────────────────────────────────────────────────────────

interface UsersTableProps {
  users: CrossTenantUserItem[];
  isLoading: boolean;
}

/**
 * Skeleton rows shown while the query is in-flight.
 */
function UserSkeletonRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i}>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-44" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-28" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-28" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-5 w-24 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-36" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-5 w-20 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-4 w-32" />
          </td>
          <td className="px-4 py-3">
            <Skeleton className="h-5 w-24 rounded-full" />
          </td>
        </tr>
      ))}
    </>
  );
}

function UsersTable({ users, isLoading }: UsersTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" aria-label="Resultados de busqueda de usuarios">
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Email
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Nombre
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Apellido
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Rol
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Clinica
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Estado
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Ultimo acceso
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">
              Multi-clinica
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {isLoading ? (
            <UserSkeletonRows />
          ) : (
            users.map((user) => (
              <tr
                key={`${user.user_id}-${user.tenant_id}`}
                className="hover:bg-[hsl(var(--muted))] transition-colors"
              >
                {/* Email */}
                <td className="px-4 py-3 text-sm text-foreground break-all">
                  {user.email}
                </td>

                {/* Nombre */}
                <td className="px-4 py-3 text-sm text-foreground">
                  {user.first_name || (
                    <span className="text-muted-foreground italic">—</span>
                  )}
                </td>

                {/* Apellido */}
                <td className="px-4 py-3 text-sm text-foreground">
                  {user.last_name || (
                    <span className="text-muted-foreground italic">—</span>
                  )}
                </td>

                {/* Rol */}
                <td className="px-4 py-3">
                  <RoleBadge role={user.role} />
                </td>

                {/* Clinica */}
                <td className="px-4 py-3 text-sm text-foreground">
                  {user.tenant_name}
                </td>

                {/* Estado */}
                <td className="px-4 py-3">
                  <StatusBadge status={user.status} />
                </td>

                {/* Ultimo acceso */}
                <td className="px-4 py-3 text-sm text-muted-foreground tabular-nums whitespace-nowrap">
                  {formatLastLogin(user.last_login_at)}
                </td>

                {/* Multi-clinica */}
                <td className="px-4 py-3">
                  {user.is_multi_clinic ? <MultiClinicBadge /> : null}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────────

/**
 * Admin cross-tenant user search page (SA-U01).
 *
 * State:
 * - searchInput: raw input string (not debounced).
 * - debouncedSearch: debounced value passed to the hook (300ms, min 2 chars).
 * - roleFilter: "all" or a specific role string.
 * - page: current page number (resets to 1 when filters change).
 *
 * The TanStack Query hook is disabled until debouncedSearch.length >= 2.
 * Until then, the empty-state prompt is shown instead of the table.
 */
export default function AdminUsersPage() {
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [page, setPage] = useState(1);

  // ── Debounced search (300ms) ───────────────────────────────────────────────
  // We intentionally use setTimeout directly (without useEffect) to keep the
  // hook count stable and avoid stale-closure issues. The ref ensures the
  // previous timer is always cancelled before scheduling a new one.
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setSearchInput(value);

    if (debounceTimer) clearTimeout(debounceTimer);

    const timer = setTimeout(() => {
      setDebouncedSearch(value.trim());
      setPage(1);
    }, 300);

    setDebounceTimer(timer);
  }

  function handleRoleChange(value: string) {
    setRoleFilter(value);
    setPage(1);
  }

  // ── Data ──────────────────────────────────────────────────────────────────
  const { data, isLoading, isFetching, isError, refetch } =
    useCrossTenantUserSearch(
      debouncedSearch,
      page,
      PAGE_SIZE,
      roleFilter !== "all" ? roleFilter : undefined,
    );

  const hasQuery = debouncedSearch.length >= 2;
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;
  const showSpinner = hasQuery && (isLoading || isFetching);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* ── Page title ── */}
      <div className="flex items-center gap-3">
        <Users
          className="h-7 w-7 text-muted-foreground shrink-0"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Buscar Usuarios
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {hasQuery && data
              ? `${data.total} ${data.total === 1 ? "usuario encontrado" : "usuarios encontrados"}`
              : "Buscar usuarios en todas las clinicas"}
          </p>
        </div>
      </div>

      {/* ── Search bar + Role filter ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search input */}
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
            aria-hidden="true"
          />
          {/* Loading spinner overlaid on the right side of the search input */}
          {showSpinner && (
            <div
              className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin rounded-full border-2 border-[hsl(var(--border))] border-t-primary-600"
              role="status"
              aria-label="Cargando resultados"
            />
          )}
          <Input
            type="search"
            placeholder="Buscar por email, nombre o apellido..."
            value={searchInput}
            onChange={handleSearchChange}
            className="pl-9"
            aria-label="Buscar usuarios"
          />
        </div>

        {/* Role filter */}
        <Select value={roleFilter} onValueChange={handleRoleChange}>
          <SelectTrigger className="w-full sm:w-52" aria-label="Filtrar por rol">
            <SelectValue placeholder="Todos los roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los roles</SelectItem>
            {ROLE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* ── Error state ── */}
      {isError && hasQuery && (
        <Card className="border-destructive-200 dark:border-destructive-700/40">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive-600 dark:text-destructive-400">
              No se pudo cargar los resultados. Verifica tu conexion e intenta de nuevo.
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

      {/* ── Empty prompt (query too short) ── */}
      {!hasQuery && (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-6 py-14 text-center">
          <Search
            className="mx-auto mb-4 h-10 w-10 text-muted-foreground opacity-40"
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">
            Ingresa al menos 2 caracteres para buscar
          </p>
        </div>
      )}

      {/* ── Results table ── */}
      {hasQuery && !isError && (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
          <UsersTable
            users={data?.items ?? []}
            isLoading={isLoading}
          />

          {/* No results (query ran but returned empty) */}
          {!isLoading && data && data.items.length === 0 && (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No se encontraron usuarios con los filtros actuales.
            </p>
          )}
        </div>
      )}

      {/* ── Pagination ── */}
      {hasQuery && !isError && data && data.total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Pagina {page} de {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || isLoading || isFetching}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || isLoading || isFetching}
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
