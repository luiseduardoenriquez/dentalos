"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  Receipt,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { useInvoices } from "@/lib/hooks/use-invoices";
import type { InvoiceResponse } from "@/lib/hooks/use-invoices";
import { usePatient } from "@/lib/hooks/use-patients";
import { formatDate, formatCurrency, cn } from "@/lib/utils";

// ─── Status Badge ─────────────────────────────────────────────────────────────

const INVOICE_STATUS_LABELS: Record<InvoiceResponse["status"], string> = {
  draft: "Borrador",
  sent: "Enviada",
  partial: "Parcial",
  paid: "Pagada",
  overdue: "Vencida",
  cancelled: "Cancelada",
};

function InvoiceStatusBadge({ status }: { status: InvoiceResponse["status"] }) {
  const variants: Record<InvoiceResponse["status"], string> = {
    draft:
      "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
    sent: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
    partial:
      "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
    paid: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    overdue:
      "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
    cancelled:
      "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] line-through",
  };

  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", variants[status])}
    >
      {INVOICE_STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function InvoicesListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-32" />
      </div>
      <Skeleton className="h-56 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InvoicesPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 20;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: invoicesData, isLoading: isLoadingInvoices } =
    useInvoices(patientId, page, PAGE_SIZE);

  const isLoading = isLoadingPatient || isLoadingInvoices;
  const invoices = invoicesData?.items ?? [];

  if (isLoading) {
    return <InvoicesListSkeleton />;
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
      {/* Breadcrumb */}
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
        <span className="text-foreground font-medium">Facturas</span>
      </nav>

      {/* Header */}
      <div className="flex items-center gap-2">
        <Receipt className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">Facturas</h1>
        {invoicesData && (
          <Badge variant="secondary" className="text-xs">
            {invoicesData.total}
          </Badge>
        )}
      </div>

      {/* Invoices Table */}
      {invoices.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title="Sin facturas"
          description="Las facturas se crean desde cotizaciones aprobadas o manualmente."
          action={{
            label: "Ver cotizaciones",
            href: `/patients/${patientId}/quotations`,
          }}
        />
      ) : (
        <>
          <DataTable
            rowKey="id"
            data={invoices as unknown as Record<string, unknown>[]}
            onRowClick={(row) =>
              router.push(
                `/patients/${patientId}/invoices/${row["id"]}`,
              )
            }
            columns={[
              {
                key: "invoice_number",
                header: "Número",
                cell: (row) => {
                  const inv = row as unknown as InvoiceResponse;
                  return (
                    <span className="font-mono text-sm font-medium text-foreground">
                      {inv.invoice_number}
                    </span>
                  );
                },
              },
              {
                key: "status",
                header: "Estado",
                cell: (row) => {
                  const inv = row as unknown as InvoiceResponse;
                  return <InvoiceStatusBadge status={inv.status} />;
                },
              },
              {
                key: "total",
                header: "Total",
                cellClassName: "text-right tabular-nums",
                cell: (row) => {
                  const inv = row as unknown as InvoiceResponse;
                  return (
                    <span className="text-sm font-semibold">
                      {formatCurrency(inv.total, "COP")}
                    </span>
                  );
                },
              },
              {
                key: "balance",
                header: "Saldo",
                cellClassName: "text-right tabular-nums",
                cell: (row) => {
                  const inv = row as unknown as InvoiceResponse;
                  return (
                    <span
                      className={cn(
                        "text-sm",
                        inv.balance > 0
                          ? "text-orange-600 font-medium"
                          : "text-green-600 font-medium",
                      )}
                    >
                      {formatCurrency(inv.balance, "COP")}
                    </span>
                  );
                },
              },
              {
                key: "due_date",
                header: "Vence",
                cell: (row) => {
                  const inv = row as unknown as InvoiceResponse;
                  if (!inv.due_date) {
                    return (
                      <span className="text-sm text-[hsl(var(--muted-foreground))]">
                        —
                      </span>
                    );
                  }
                  const isOverdue =
                    inv.status === "overdue" ||
                    (inv.days_until_due !== null && inv.days_until_due < 0);
                  return (
                    <span
                      className={cn(
                        "text-sm",
                        isOverdue
                          ? "text-red-600 font-medium"
                          : "text-[hsl(var(--muted-foreground))]",
                      )}
                    >
                      {formatDate(inv.due_date)}
                    </span>
                  );
                },
              },
              {
                key: "created_at",
                header: "Fecha",
                cell: (row) => {
                  const inv = row as unknown as InvoiceResponse;
                  return (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatDate(inv.created_at)}
                    </span>
                  );
                },
              },
            ]}
          />

          {/* Pagination */}
          {invoicesData && invoicesData.total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={invoicesData.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}
