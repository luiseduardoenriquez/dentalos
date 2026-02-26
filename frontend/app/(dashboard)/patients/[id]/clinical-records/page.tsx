"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  FilePlus,
  ClipboardList,
  AlertCircle,
  Stethoscope,
  FileText,
  Scissors,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import {
  useClinicalRecords,
  type ClinicalRecordListItem,
} from "@/lib/hooks/use-clinical-records";
import { formatDate } from "@/lib/utils";

// ─── Type Config ─────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<
  string,
  {
    icon: React.ElementType;
    label: string;
    badgeVariant: "default" | "secondary" | "outline" | "success" | "warning";
  }
> = {
  examination: {
    icon: Stethoscope,
    label: "Examen",
    badgeVariant: "default",
  },
  evolution_note: {
    icon: FileText,
    label: "Nota de evolución",
    badgeVariant: "success",
  },
  procedure: {
    icon: Scissors,
    label: "Procedimiento",
    badgeVariant: "warning",
  },
};

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function ClinicalRecordsListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="rounded-xl border">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-0">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Column Definitions ──────────────────────────────────────────────────────

function buildColumns(): ColumnDef<ClinicalRecordListItem>[] {
  return [
    {
      key: "type",
      header: "Tipo",
      sortable: false,
      cell: (row) => {
        const config = TYPE_CONFIG[row.type];
        if (!config) {
          return <Badge variant="secondary">{row.type}</Badge>;
        }
        const Icon = config.icon;
        return (
          <div className="flex items-center gap-2">
            <Icon className="h-3.5 w-3.5 shrink-0 text-[hsl(var(--muted-foreground))]" />
            <Badge variant={config.badgeVariant} className="text-xs">
              {config.label}
            </Badge>
          </div>
        );
      },
    },
    {
      key: "created_at",
      header: "Fecha",
      sortable: false,
      cell: (row) => (
        <span className="text-sm font-medium text-foreground">
          {formatDate(row.created_at)}
        </span>
      ),
    },
    {
      key: "doctor_name",
      header: "Doctor",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))]">
          {row.doctor_name ?? "—"}
        </span>
      ),
    },
    {
      key: "tooth_numbers",
      header: "Diente(s)",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))] font-mono">
          {row.tooth_numbers && row.tooth_numbers.length > 0
            ? row.tooth_numbers.join(", ")
            : "—"}
        </span>
      ),
    },
    {
      key: "is_editable",
      header: "",
      cell: (row) =>
        !row.is_editable ? (
          <span title="Bloqueado (no editable)">
            <Lock className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
          </span>
        ) : null,
    },
  ];
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function ClinicalRecordsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [page, setPage] = React.useState(1);
  const [typeFilter, setTypeFilter] = React.useState<string>("");
  const PAGE_SIZE = 20;

  const activeType = typeFilter && typeFilter !== "all" ? typeFilter : undefined;

  const { data, isLoading, isError } = useClinicalRecords(
    params.id,
    page,
    PAGE_SIZE,
    activeType,
  );

  const records = data?.items ?? [];
  const total = data?.total ?? 0;

  // Reset page when filter changes
  React.useEffect(() => {
    setPage(1);
  }, [typeFilter]);

  const columns = buildColumns();

  if (isLoading) {
    return <ClinicalRecordsListSkeleton />;
  }

  if (isError) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Error al cargar registros"
        description="No se pudieron cargar los registros clínicos. Intenta de nuevo."
      />
    );
  }

  const isEmpty = total === 0;

  return (
    <div className="space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${params.id}`}
          className="hover:text-foreground transition-colors"
        >
          Detalle del paciente
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Registros clínicos</span>
      </nav>

      {/* ─── Page Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Registros clínicos
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Exámenes, notas de evolución y procedimientos del paciente.
          </p>
        </div>
        <Button asChild>
          <Link href={`/patients/${params.id}/clinical-records/new`}>
            <FilePlus className="mr-2 h-4 w-4" />
            Nuevo registro
          </Link>
        </Button>
      </div>

      {/* ─── Type Filter ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-[hsl(var(--muted-foreground))]">Filtrar por tipo:</span>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[200px]" aria-label="Filtrar por tipo de registro">
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="examination">Examen</SelectItem>
            <SelectItem value="evolution_note">Nota de evolución</SelectItem>
            <SelectItem value="procedure">Procedimiento</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ─── Table or Empty State ────────────────────────────────────────── */}
      {isEmpty ? (
        <EmptyState
          icon={ClipboardList}
          title="Sin registros clínicos"
          description="Este paciente no tiene registros clínicos. Crea el primero."
          action={{
            label: "Nuevo registro",
            href: `/patients/${params.id}/clinical-records/new`,
          }}
        />
      ) : (
        <>
          <DataTable<ClinicalRecordListItem>
            columns={columns}
            data={records}
            loading={isLoading}
            skeletonRows={6}
            rowKey="id"
            emptyMessage="No hay registros clínicos registrados."
          />

          {total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
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
