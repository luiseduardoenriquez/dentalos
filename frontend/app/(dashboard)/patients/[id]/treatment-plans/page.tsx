"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  Plus,
  ClipboardList,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { useTreatmentPlans } from "@/lib/hooks/use-treatment-plans";
import type { TreatmentPlanResponse } from "@/lib/hooks/use-treatment-plans";
import { usePatient } from "@/lib/hooks/use-patients";
import { formatDate, formatCurrency, cn } from "@/lib/utils";

// ─── Status Badge Helpers ─────────────────────────────────────────────────────

const PLAN_STATUS_LABELS: Record<TreatmentPlanResponse["status"], string> = {
  draft: "Borrador",
  active: "Activo",
  completed: "Completado",
  cancelled: "Cancelado",
};

function PlanStatusBadge({ status }: { status: TreatmentPlanResponse["status"] }) {
  const variants: Record<TreatmentPlanResponse["status"], string> = {
    draft: "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
    active: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
    completed: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    cancelled: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
  };
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", variants[status])}>
      {PLAN_STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function ProgressBar({ value }: { value: number }) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-[hsl(var(--muted))]">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            clamped === 100
              ? "bg-green-500"
              : clamped > 50
              ? "bg-blue-500"
              : "bg-primary-600",
          )}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums w-8 text-right">
        {clamped}%
      </span>
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function TreatmentPlansListSkeleton() {
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

export default function TreatmentPlansPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 20;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: plansData, isLoading: isLoadingPlans } = useTreatmentPlans(
    patientId,
    page,
    PAGE_SIZE,
  );

  const isLoading = isLoadingPatient || isLoadingPlans;
  const plans = plansData?.items ?? [];

  if (isLoading) {
    return <TreatmentPlansListSkeleton />;
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
        <span className="text-foreground font-medium">Planes de tratamiento</span>
      </nav>

      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Planes de tratamiento
          </h1>
          {plansData && (
            <Badge variant="secondary" className="text-xs">
              {plansData.total}
            </Badge>
          )}
        </div>
        <Button asChild size="sm">
          <Link href={`/patients/${patientId}/treatment-plans/new`}>
            <Plus className="mr-1.5 h-4 w-4" />
            Nuevo plan
          </Link>
        </Button>
      </div>

      {/* ─── Plans Table ─────────────────────────────────────────────────── */}
      {plans.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="Sin planes de tratamiento"
          description="Crea el primer plan de tratamiento para este paciente."
          action={{
            label: "Nuevo plan",
            href: `/patients/${patientId}/treatment-plans/new`,
          }}
        />
      ) : (
        <>
          <DataTable
            rowKey="id"
            data={plans as unknown as Record<string, unknown>[]}
            onRowClick={(row) =>
              router.push(
                `/patients/${patientId}/treatment-plans/${row["id"]}`,
              )
            }
            columns={[
              {
                key: "name",
                header: "Nombre",
                cell: (row) => {
                  const plan = row as unknown as TreatmentPlanResponse;
                  return (
                    <div className="space-y-0.5">
                      <p className="font-medium text-sm text-foreground">
                        {plan.name}
                      </p>
                      {plan.description && (
                        <p className="text-xs text-[hsl(var(--muted-foreground))] truncate max-w-[200px]">
                          {plan.description}
                        </p>
                      )}
                    </div>
                  );
                },
              },
              {
                key: "status",
                header: "Estado",
                cell: (row) => {
                  const plan = row as unknown as TreatmentPlanResponse;
                  return <PlanStatusBadge status={plan.status} />;
                },
              },
              {
                key: "progress_percent",
                header: "Progreso",
                cellClassName: "min-w-[140px]",
                cell: (row) => {
                  const plan = row as unknown as TreatmentPlanResponse;
                  return <ProgressBar value={plan.progress_percent} />;
                },
              },
              {
                key: "total_cost_estimated",
                header: "Costo estimado",
                cellClassName: "text-right tabular-nums",
                cell: (row) => {
                  const plan = row as unknown as TreatmentPlanResponse;
                  return (
                    <span className="text-sm font-medium">
                      {formatCurrency(plan.total_cost_estimated, "COP")}
                    </span>
                  );
                },
              },
              {
                key: "created_at",
                header: "Fecha",
                cell: (row) => {
                  const plan = row as unknown as TreatmentPlanResponse;
                  return (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatDate(plan.created_at)}
                    </span>
                  );
                },
              },
            ]}
          />

          {/* Pagination */}
          {plansData && plansData.total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={plansData.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}
