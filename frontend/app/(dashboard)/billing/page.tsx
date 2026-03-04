"use client";

import * as React from "react";
import Link from "next/link";
import {
  Receipt,
  AlertTriangle,
  TrendingUp,
  CreditCard,
  Clock,
  ExternalLink,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface BillingSummary {
  total_pending: number;
  total_overdue: number;
  collected_month: number;
  collected_year: number;
  invoice_count: number;
  overdue_count: number;
}

interface InvoiceSummaryItem {
  id: string;
  invoice_number: string;
  patient_id: string;
  patient_name: string;
  total: number;
  balance: number;
  status: string;
  due_date: string | null;
  created_at: string;
}

interface InvoiceSummaryList {
  items: InvoiceSummaryItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status Badge ────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  draft: "Borrador",
  sent: "Enviada",
  partial: "Parcial",
  paid: "Pagada",
  overdue: "Vencida",
  cancelled: "Cancelada",
};

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "success" | "destructive"> = {
  draft: "secondary",
  sent: "default",
  partial: "default",
  paid: "success",
  overdue: "destructive",
  cancelled: "secondary",
};

// ─── Summary Card ─────────────────────────────────────────────────────────────

function SummaryCard({
  title,
  value,
  icon: Icon,
  variant = "default",
}: {
  title: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  variant?: "default" | "warning" | "success";
}) {
  const variantStyles = {
    default:
      "bg-[hsl(var(--card))] border-[hsl(var(--border))]",
    warning:
      "bg-orange-50 border-orange-200 dark:bg-orange-900/10 dark:border-orange-800",
    success:
      "bg-green-50 border-green-200 dark:bg-green-900/10 dark:border-green-800",
  };

  const iconStyles = {
    default: "text-primary-600",
    warning: "text-orange-600",
    success: "text-green-600",
  };

  return (
    <div
      className={cn(
        "rounded-xl border p-5 transition-shadow hover:shadow-sm",
        variantStyles[variant],
      )}
    >
      <div className="flex items-center gap-3 mb-3">
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg",
            variant === "default" && "bg-primary-100 dark:bg-primary-900/30",
            variant === "warning" && "bg-orange-100 dark:bg-orange-900/30",
            variant === "success" && "bg-green-100 dark:bg-green-900/30",
          )}
        >
          <Icon className={cn("h-4.5 w-4.5", iconStyles[variant])} />
        </div>
        <span className="text-sm text-[hsl(var(--muted-foreground))]">
          {title}
        </span>
      </div>
      <p className="text-2xl font-bold tabular-nums text-foreground">{value}</p>
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function BillingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-7 w-40" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

// ─── Invoice Table Columns ────────────────────────────────────────────────────

const invoiceColumns: ColumnDef<InvoiceSummaryItem>[] = [
  {
    key: "invoice_number",
    header: "Factura",
    cell: (row) => (
      <span className="text-sm font-medium text-foreground">{row.invoice_number}</span>
    ),
  },
  {
    key: "patient_name",
    header: "Paciente",
    cell: (row) => (
      <Link
        href={`/patients/${row.patient_id}`}
        className="text-sm text-primary-600 hover:text-primary-700 hover:underline"
      >
        {row.patient_name}
      </Link>
    ),
  },
  {
    key: "created_at",
    header: "Fecha",
    cell: (row) => (
      <span className="text-sm text-[hsl(var(--muted-foreground))]">
        {formatDate(row.created_at)}
      </span>
    ),
  },
  {
    key: "total",
    header: "Total",
    cell: (row) => (
      <span className="text-sm font-medium tabular-nums text-foreground">
        {formatCurrency(row.total)}
      </span>
    ),
  },
  {
    key: "status",
    header: "Estado",
    cell: (row) => (
      <Badge variant={STATUS_VARIANTS[row.status] ?? "default"} className="text-xs">
        {STATUS_LABELS[row.status] ?? row.status}
      </Badge>
    ),
  },
  {
    key: "actions",
    header: "",
    cell: (row) => (
      <Link
        href={`/patients/${row.patient_id}/invoices`}
        className="text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors"
        title="Ver detalle"
      >
        <ExternalLink className="h-4 w-4" />
      </Link>
    ),
  },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const [invoicePage, setInvoicePage] = React.useState(1);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["billing", "summary"],
    queryFn: () => apiGet<BillingSummary>("/billing/summary"),
    staleTime: 60_000,
  });

  const { data: invoices, isLoading: invoicesLoading } = useQuery({
    queryKey: ["billing", "invoices", invoicePage],
    queryFn: () =>
      apiGet<InvoiceSummaryList>("/billing/invoices", {
        page: invoicePage,
        page_size: 20,
      }),
    staleTime: 30_000,
  });

  if (isLoading || !summary) {
    return <BillingSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Pendiente"
          value={formatCurrency(summary.total_pending)}
          icon={Clock}
        />
        <SummaryCard
          title="Vencido"
          value={formatCurrency(summary.total_overdue)}
          icon={AlertTriangle}
          variant={summary.total_overdue > 0 ? "warning" : "default"}
        />
        <SummaryCard
          title="Recaudado (mes)"
          value={formatCurrency(summary.collected_month)}
          icon={CreditCard}
          variant="success"
        />
        <SummaryCard
          title="Recaudado (año)"
          value={formatCurrency(summary.collected_year)}
          icon={TrendingUp}
          variant="success"
        />
      </div>

      {/* Quick Stats */}
      <div className="flex gap-4 text-sm text-[hsl(var(--muted-foreground))]">
        <span>
          <strong className="text-foreground">{summary.invoice_count}</strong>{" "}
          facturas pendientes
        </span>
        {summary.overdue_count > 0 && (
          <span className="text-orange-600">
            <strong>{summary.overdue_count}</strong> vencidas
          </span>
        )}
      </div>

      {/* Invoice Table */}
      {invoices && invoices.items.length > 0 ? (
        <>
          <DataTable<InvoiceSummaryItem>
            columns={invoiceColumns}
            data={invoices.items}
            loading={invoicesLoading}
            skeletonRows={5}
            rowKey="id"
            emptyMessage="No hay facturas."
          />
          {invoices.total > 20 && (
            <Pagination
              page={invoicePage}
              pageSize={20}
              total={invoices.total}
              onChange={setInvoicePage}
            />
          )}
        </>
      ) : (
        <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-8 text-center">
          <Receipt className="h-10 w-10 mx-auto text-[hsl(var(--muted-foreground))] opacity-50 mb-3" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            No hay facturas aún. Crea una factura desde el perfil de un paciente.
          </p>
          <Link
            href="/patients"
            className="inline-block mt-3 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
          >
            Ir a pacientes
          </Link>
        </div>
      )}
    </div>
  );
}
