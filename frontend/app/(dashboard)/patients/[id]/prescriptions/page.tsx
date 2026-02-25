"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChevronRight, FilePlus, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import { usePrescriptions, type PrescriptionResponse } from "@/lib/hooks/use-prescriptions";
import { formatDate, truncate } from "@/lib/utils";

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function PrescriptionsListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="rounded-xl border">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-0">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-48" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Column Definitions ───────────────────────────────────────────────────────

function buildColumns(
  onRowClick: (prescription: PrescriptionResponse) => void,
): ColumnDef<PrescriptionResponse>[] {
  return [
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
      key: "medications",
      header: "Medicamentos",
      cell: (row) => (
        <Badge variant="secondary" className="text-xs">
          {row.medications.length}{" "}
          {row.medications.length === 1 ? "medicamento" : "medicamentos"}
        </Badge>
      ),
    },
    {
      key: "diagnosis_id",
      header: "Diagnóstico",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))]">
          {row.diagnosis_id ? (
            <Badge variant="outline" className="text-xs font-mono">
              {row.diagnosis_id.slice(0, 8)}…
            </Badge>
          ) : (
            "—"
          )}
        </span>
      ),
    },
    {
      key: "notes",
      header: "Notas",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))]">
          {row.notes ? truncate(row.notes, 60) : <span>—</span>}
        </span>
      ),
    },
    {
      key: "is_active",
      header: "Estado",
      cell: (row) =>
        row.is_active ? (
          <Badge variant="success">Activa</Badge>
        ) : (
          <Badge variant="secondary">Inactiva</Badge>
        ),
    },
  ];
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PrescriptionsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 20;

  const { data, isLoading, isError } = usePrescriptions(params.id, page, PAGE_SIZE);

  const prescriptions = data?.items ?? [];
  const total = data?.total ?? 0;

  function handleRowClick(prescription: PrescriptionResponse) {
    router.push(`/patients/${params.id}/prescriptions/${prescription.id}`);
  }

  const columns = buildColumns(handleRowClick);

  if (isLoading) {
    return <PrescriptionsListSkeleton />;
  }

  if (isError) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Error al cargar prescripciones"
        description="No se pudieron cargar las prescripciones. Intenta de nuevo."
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
        <span className="text-foreground font-medium">Prescripciones</span>
      </nav>

      {/* ─── Page Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Prescripciones</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Historial de prescripciones médicas del paciente.
          </p>
        </div>
        <Button asChild>
          <Link href={`/patients/${params.id}/prescriptions/new`}>
            <FilePlus className="mr-2 h-4 w-4" />
            Nueva prescripción
          </Link>
        </Button>
      </div>

      {/* ─── Table or Empty State ────────────────────────────────────────── */}
      {isEmpty ? (
        <EmptyState
          icon={FileText}
          title="Sin prescripciones"
          description="Este paciente no tiene prescripciones registradas. Crea la primera."
          action={{
            label: "Nueva prescripción",
            href: `/patients/${params.id}/prescriptions/new`,
          }}
        />
      ) : (
        <>
          <DataTable<PrescriptionResponse>
            columns={columns}
            data={prescriptions}
            loading={isLoading}
            skeletonRows={6}
            rowKey="id"
            onRowClick={handleRowClick}
            emptyMessage="No hay prescripciones registradas."
          />

          {total > 0 && (
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
