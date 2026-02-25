"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  ReceiptText,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { useQuotations } from "@/lib/hooks/use-quotations";
import type { QuotationResponse } from "@/lib/hooks/use-quotations";
import { usePatient } from "@/lib/hooks/use-patients";
import { formatDate, formatCurrency, cn } from "@/lib/utils";

// ─── Status Badge Helpers ─────────────────────────────────────────────────────

const QUOTATION_STATUS_LABELS: Record<QuotationResponse["status"], string> = {
  draft: "Borrador",
  sent: "Enviada",
  approved: "Aprobada",
  rejected: "Rechazada",
  expired: "Vencida",
};

function QuotationStatusBadge({
  status,
  days_until_expiry,
}: {
  status: QuotationResponse["status"];
  days_until_expiry: number | null;
}) {
  const variants: Record<QuotationResponse["status"], string> = {
    draft:
      "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
    sent: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
    approved:
      "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    rejected:
      "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
    expired:
      "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-700",
  };

  // Warn if expiring soon (< 7 days) and still active
  const isExpiringSoon =
    (status === "draft" || status === "sent") &&
    days_until_expiry !== null &&
    days_until_expiry >= 0 &&
    days_until_expiry < 7;

  return (
    <div className="flex items-center gap-1.5">
      <Badge
        variant="outline"
        className={cn("text-xs font-medium", variants[status])}
      >
        {QUOTATION_STATUS_LABELS[status]}
      </Badge>
      {isExpiringSoon && (
        <span
          title={`Vence en ${days_until_expiry} día${days_until_expiry !== 1 ? "s" : ""}`}
          className="text-orange-500"
        >
          <Clock className="h-3.5 w-3.5" />
        </span>
      )}
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function QuotationsListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-36" />
      </div>
      <Skeleton className="h-56 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function QuotationsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 20;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: quotationsData, isLoading: isLoadingQuotations } =
    useQuotations(patientId, page, PAGE_SIZE);

  const isLoading = isLoadingPatient || isLoadingQuotations;
  const quotations = quotationsData?.items ?? [];

  if (isLoading) {
    return <QuotationsListSkeleton />;
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
        <Link
          href="/patients"
          className="hover:text-foreground transition-colors"
        >
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
        <span className="text-foreground font-medium">Cotizaciones</span>
      </nav>

      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <ReceiptText className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">Cotizaciones</h1>
        {quotationsData && (
          <Badge variant="secondary" className="text-xs">
            {quotationsData.total}
          </Badge>
        )}
      </div>

      {/* ─── Quotations Table ────────────────────────────────────────────── */}
      {quotations.length === 0 ? (
        <EmptyState
          icon={ReceiptText}
          title="Sin cotizaciones"
          description="Las cotizaciones se generan desde un plan de tratamiento activo."
          action={{
            label: "Ver planes de tratamiento",
            href: `/patients/${patientId}/treatment-plans`,
          }}
        />
      ) : (
        <>
          <DataTable
            rowKey="id"
            data={quotations as unknown as Record<string, unknown>[]}
            onRowClick={(row) =>
              router.push(
                `/patients/${patientId}/quotations/${row["id"]}`,
              )
            }
            columns={[
              {
                key: "quotation_number",
                header: "Número",
                cell: (row) => {
                  const q = row as unknown as QuotationResponse;
                  return (
                    <span className="font-mono text-sm font-medium text-foreground">
                      {q.quotation_number}
                    </span>
                  );
                },
              },
              {
                key: "status",
                header: "Estado",
                cell: (row) => {
                  const q = row as unknown as QuotationResponse;
                  return (
                    <QuotationStatusBadge
                      status={q.status}
                      days_until_expiry={q.days_until_expiry}
                    />
                  );
                },
              },
              {
                key: "total",
                header: "Total",
                cellClassName: "text-right tabular-nums",
                cell: (row) => {
                  const q = row as unknown as QuotationResponse;
                  return (
                    <span className="text-sm font-semibold">
                      {formatCurrency(q.total, "COP")}
                    </span>
                  );
                },
              },
              {
                key: "valid_until",
                header: "Válido hasta",
                cell: (row) => {
                  const q = row as unknown as QuotationResponse;
                  const isExpiringSoon =
                    (q.status === "draft" || q.status === "sent") &&
                    q.days_until_expiry !== null &&
                    q.days_until_expiry >= 0 &&
                    q.days_until_expiry < 7;
                  return (
                    <span
                      className={cn(
                        "text-sm",
                        isExpiringSoon
                          ? "text-orange-600 font-medium"
                          : "text-[hsl(var(--muted-foreground))]",
                      )}
                    >
                      {formatDate(q.valid_until)}
                      {isExpiringSoon && q.days_until_expiry !== null && (
                        <span className="ml-1 text-xs">
                          ({q.days_until_expiry}d)
                        </span>
                      )}
                    </span>
                  );
                },
              },
              {
                key: "created_at",
                header: "Fecha",
                cell: (row) => {
                  const q = row as unknown as QuotationResponse;
                  return (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatDate(q.created_at)}
                    </span>
                  );
                },
              },
            ]}
          />

          {/* Pagination */}
          {quotationsData && quotationsData.total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={quotationsData.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}
