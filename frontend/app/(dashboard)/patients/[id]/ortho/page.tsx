"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  Plus,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { useOrthoCases } from "@/lib/hooks/use-ortho";
import type { OrthoCaseListItem } from "@/lib/hooks/use-ortho";
import { usePatient } from "@/lib/hooks/use-patients";
import { OrthoStatusBadge } from "@/components/ortho/ortho-status-badge";
import { APPLIANCE_TYPE_LABELS } from "@/lib/validations/ortho";
import { formatDate, formatCurrency } from "@/lib/utils";

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function OrthoListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-36" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-9 w-32 rounded-md" />
      </div>
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OrthoPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 20;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: casesData, isLoading: isLoadingCases } = useOrthoCases(
    patientId,
    page,
    PAGE_SIZE,
  );

  const isLoading = isLoadingPatient || isLoadingCases;
  const cases = casesData?.items ?? [];

  if (isLoading) {
    return <OrthoListSkeleton />;
  }

  if (!patient) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Paciente no encontrado"
        description="El paciente que buscas no existe o no tienes permiso para verlo."
        action={{ label: "Volver a pacientes", href: "/patients" }}
      />
    );
  }

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
          href={`/patients/${patientId}`}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {patient.full_name}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Ortodoncia</span>
      </nav>

      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Ortodoncia
          </h1>
          {casesData && (
            <Badge variant="secondary" className="text-xs">
              {casesData.total}
            </Badge>
          )}
        </div>
        <Button asChild size="sm">
          <Link href={`/patients/${patientId}/ortho/new`}>
            <Plus className="mr-1.5 h-4 w-4" />
            Nuevo caso
          </Link>
        </Button>
      </div>

      {/* ─── Cases Table ─────────────────────────────────────────────────── */}
      {cases.length === 0 ? (
        <EmptyState
          icon={Wrench}
          title="Sin casos de ortodoncia"
          description="Crea el primer caso de ortodoncia para este paciente."
          action={{
            label: "Nuevo caso",
            href: `/patients/${patientId}/ortho/new`,
          }}
        />
      ) : (
        <>
          <DataTable
            rowKey="id"
            data={cases as unknown as Record<string, unknown>[]}
            onRowClick={(row) =>
              router.push(`/patients/${patientId}/ortho/${row["id"]}`)
            }
            columns={[
              {
                key: "case_number",
                header: "Caso",
                cell: (row) => {
                  const c = row as unknown as OrthoCaseListItem;
                  return (
                    <span className="font-medium text-sm text-foreground tabular-nums">
                      {c.case_number}
                    </span>
                  );
                },
              },
              {
                key: "status",
                header: "Estado",
                cell: (row) => {
                  const c = row as unknown as OrthoCaseListItem;
                  return <OrthoStatusBadge status={c.status} />;
                },
              },
              {
                key: "appliance_type",
                header: "Aparatología",
                cell: (row) => {
                  const c = row as unknown as OrthoCaseListItem;
                  return (
                    <span className="text-sm text-foreground">
                      {APPLIANCE_TYPE_LABELS[c.appliance_type] ?? c.appliance_type}
                    </span>
                  );
                },
              },
              {
                key: "total_cost_estimated",
                header: "Costo estimado",
                cellClassName: "text-right tabular-nums",
                cell: (row) => {
                  const c = row as unknown as OrthoCaseListItem;
                  return (
                    <span className="text-sm font-medium">
                      {formatCurrency(c.total_cost_estimated, "COP")}
                    </span>
                  );
                },
              },
              {
                key: "visit_count",
                header: "Visitas",
                cellClassName: "text-right tabular-nums",
                cell: (row) => {
                  const c = row as unknown as OrthoCaseListItem;
                  return (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                      {c.visit_count}
                    </span>
                  );
                },
              },
              {
                key: "created_at",
                header: "Fecha",
                cell: (row) => {
                  const c = row as unknown as OrthoCaseListItem;
                  return (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatDate(c.created_at)}
                    </span>
                  );
                },
              },
            ]}
          />

          {/* Pagination */}
          {casesData && casesData.total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={casesData.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}
