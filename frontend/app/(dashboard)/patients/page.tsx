"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserPlus, Users, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import {
  usePatients,
  type PatientListItem,
  type PatientsQueryParams,
} from "@/lib/hooks/use-patients";
import { formatDate, getInitials } from "@/lib/utils";

// ─── Filter Options ───────────────────────────────────────────────────────────

type ActiveFilter = "all" | "active" | "inactive";

const ACTIVE_FILTER_OPTIONS: { value: ActiveFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "inactive", label: "Inactivos" },
];

// ─── Column Definitions ───────────────────────────────────────────────────────

function buildColumns(
  onRowClick: (patient: PatientListItem) => void,
): ColumnDef<PatientListItem>[] {
  return [
    {
      key: "full_name",
      header: "Nombre completo",
      sortable: true,
      cell: (row) => (
        <div className="flex items-center gap-3 min-w-0">
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="text-xs">{getInitials(row.full_name)}</AvatarFallback>
          </Avatar>
          <span className="font-medium text-foreground truncate">{row.full_name}</span>
        </div>
      ),
    },
    {
      key: "document_number",
      header: "Documento",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))]">
          <span className="font-medium text-foreground">{row.document_type}</span>{" "}
          {row.document_number}
        </span>
      ),
    },
    {
      key: "phone",
      header: "Teléfono",
      cell: (row) => (
        <span className="text-sm">{row.phone ?? <span className="text-[hsl(var(--muted-foreground))]">—</span>}</span>
      ),
    },
    {
      key: "email",
      header: "Correo electrónico",
      cell: (row) => (
        <span className="text-sm truncate max-w-[200px] block">
          {row.email ?? <span className="text-[hsl(var(--muted-foreground))]">—</span>}
        </span>
      ),
    },
    {
      key: "eps_status",
      header: "EPS",
      cell: (row) => {
        const status = (row as PatientListItem & { eps_status?: string }).eps_status;
        if (!status || status === "pending") {
          return <Badge variant="outline" className="text-xs">Pendiente</Badge>;
        }
        if (status === "active") {
          return <Badge variant="success" className="text-xs">Activa</Badge>;
        }
        if (status === "inactive") {
          return <Badge variant="destructive" className="text-xs">Inactiva</Badge>;
        }
        return <Badge variant="secondary" className="text-xs">{status}</Badge>;
      },
    },
    {
      key: "is_active",
      header: "Estado",
      cell: (row) =>
        row.is_active ? (
          <Badge variant="success">Activo</Badge>
        ) : (
          <Badge variant="secondary">Inactivo</Badge>
        ),
    },
    {
      key: "created_at",
      header: "Creado",
      sortable: true,
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))]">
          {formatDate(row.created_at)}
        </span>
      ),
    },
  ];
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientsPage() {
  const router = useRouter();

  // ─── Local State ──────────────────────────────────────────────────────────
  const [searchInput, setSearchInput] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [activeFilter, setActiveFilter] = React.useState<ActiveFilter>("all");
  const [page, setPage] = React.useState(1);
  const [sortBy, setSortBy] = React.useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = React.useState<"asc" | "desc">("asc");

  // Debounce search input (300ms)
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1); // Reset to first page on new search
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Reset to page 1 when filters change
  React.useEffect(() => {
    setPage(1);
  }, [activeFilter]);

  // ─── Query ────────────────────────────────────────────────────────────────
  const queryParams: PatientsQueryParams = {
    page,
    page_size: 20,
    search: debouncedSearch || undefined,
    is_active:
      activeFilter === "all" ? "all" : activeFilter === "active" ? true : false,
    sort_by: sortBy,
    sort_order: sortBy ? sortOrder : undefined,
  };

  const { data, isLoading } = usePatients(queryParams);

  const patients = data?.items ?? [];
  const total = data?.total ?? 0;

  // ─── Handlers ─────────────────────────────────────────────────────────────
  function handleRowClick(patient: PatientListItem) {
    router.push(`/patients/${patient.id}`);
  }

  function handleSort(key: string, direction: "asc" | "desc" | null) {
    if (!direction) {
      setSortBy(undefined);
    } else {
      setSortBy(key);
      setSortOrder(direction);
    }
  }

  const columns = buildColumns(handleRowClick);

  const sortState = sortBy ? { key: sortBy, direction: sortOrder } : undefined;

  const isEmpty = !isLoading && total === 0 && !debouncedSearch && activeFilter === "all";

  return (
    <div className="space-y-6">
      {/* ─── Page Header ───────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Pacientes</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Gestiona los pacientes registrados en la clínica.
          </p>
        </div>
        <Button asChild>
          <Link href="/patients/new">
            <UserPlus className="mr-2 h-4 w-4" />
            Nuevo paciente
          </Link>
        </Button>
      </div>

      {/* ─── Filters & Search ──────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative w-full sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          <Input
            placeholder="Buscar por nombre, documento, teléfono..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
            aria-label="Buscar pacientes"
          />
        </div>

        {/* Active filter tabs */}
        <div
          className="flex items-center gap-1 rounded-lg border border-[hsl(var(--border))] p-1 bg-[hsl(var(--muted))] w-fit"
          role="group"
          aria-label="Filtrar por estado"
        >
          {ACTIVE_FILTER_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setActiveFilter(option.value)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeFilter === option.value
                  ? "bg-white dark:bg-zinc-800 text-foreground shadow-sm"
                  : "text-[hsl(var(--muted-foreground))] hover:text-foreground"
              }`}
              aria-pressed={activeFilter === option.value}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Table or Empty State ──────────────────────────────────────── */}
      {isEmpty ? (
        <EmptyState
          icon={Users}
          title="No hay pacientes registrados"
          description="Comienza registrando el primer paciente de la clínica."
          action={{
            label: "Registrar primer paciente",
            href: "/patients/new",
          }}
        />
      ) : (
        <>
          <DataTable<PatientListItem>
            columns={columns}
            data={patients}
            loading={isLoading}
            skeletonRows={8}
            rowKey="id"
            sortState={sortState}
            onSort={handleSort}
            onRowClick={handleRowClick}
            emptyMessage={
              debouncedSearch
                ? `No se encontraron pacientes para "${debouncedSearch}"`
                : "No hay pacientes con los filtros seleccionados."
            }
          />

          {total > 0 && (
            <Pagination
              page={page}
              pageSize={20}
              total={total}
              onChange={setPage}
              className="mt-4"
            />
          )}
        </>
      )}
    </div>
  );
}
