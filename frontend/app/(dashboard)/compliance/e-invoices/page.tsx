"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { formatCurrency, formatDate } from "@/lib/utils";
import { FileText, RefreshCw } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface EInvoiceListItem {
  id: string;
  invoice_id: string;
  invoice_number: string;
  patient_name: string;
  total: number;
  status: string;
  cufe: string | null;
  created_at: string;
}

interface EInvoiceListResponse {
  items: EInvoiceListItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

function getEInvoiceStatusBadge(status: string) {
  switch (status) {
    case "pending":
      return <Badge variant="outline">Pendiente</Badge>;
    case "submitted":
      return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">Enviada</Badge>;
    case "accepted":
      return <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">Aceptada</Badge>;
    case "rejected":
      return <Badge variant="destructive">Rechazada</Badge>;
    case "error":
      return <Badge variant="destructive">Error</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

// ─── Column Definitions ──────────────────────────────────────────────────────

const columns: ColumnDef<EInvoiceListItem>[] = [
  {
    key: "invoice_number",
    header: "Factura #",
    cell: (row) => (
      <span className="text-sm font-medium text-foreground">{row.invoice_number}</span>
    ),
  },
  {
    key: "patient_name",
    header: "Paciente",
    cell: (row) => (
      <span className="text-sm text-foreground">{row.patient_name}</span>
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
    header: "Monto",
    cell: (row) => (
      <span className="text-sm font-medium tabular-nums text-foreground">
        {formatCurrency(row.total)}
      </span>
    ),
  },
  {
    key: "status",
    header: "Estado DIAN",
    cell: (row) => getEInvoiceStatusBadge(row.status),
  },
  {
    key: "cufe",
    header: "CUFE",
    cell: (row) =>
      row.cufe ? (
        <span className="text-xs text-[hsl(var(--muted-foreground))] font-mono truncate max-w-[120px] inline-block" title={row.cufe}>
          {row.cufe.slice(0, 12)}...
        </span>
      ) : (
        <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>
      ),
  },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EInvoicesPage() {
  const [page, setPage] = React.useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["compliance", "e-invoices", page],
    queryFn: () =>
      apiGet<EInvoiceListResponse>("/compliance/e-invoices", {
        page,
        page_size: 20,
      }),
    staleTime: 30_000,
  });

  const hasInvoices = data && data.items.length > 0;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">
            Facturación Electrónica DIAN
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
            Envío de facturas electrónicas a la DIAN vía MATIAS
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-1.5" />
          Actualizar
        </Button>
      </div>

      {/* E-Invoice Table */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      ) : hasInvoices ? (
        <>
          <DataTable<EInvoiceListItem>
            columns={columns}
            data={data.items}
            loading={isLoading}
            skeletonRows={5}
            rowKey="id"
            emptyMessage="No hay facturas electrónicas."
          />
          {data.total > 20 && (
            <Pagination
              page={page}
              pageSize={20}
              total={data.total}
              onChange={setPage}
            />
          )}
        </>
      ) : (
        <Card>
          <CardContent>
            <div className="text-center py-8">
              <FileText className="mx-auto h-12 w-12 text-[hsl(var(--muted-foreground))] mb-4" />
              <h3 className="text-lg font-medium mb-2">
                Sin facturas electrónicas
              </h3>
              <p className="text-sm text-[hsl(var(--muted-foreground))] max-w-md mx-auto">
                Para enviar una factura electrónica, vaya a Facturación, seleccione una factura
                y use el botón &ldquo;Enviar a DIAN&rdquo;. Las facturas enviadas aparecerán aquí.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Status legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Estados de factura electrónica</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("pending")}
              <span className="text-sm">En procesamiento</span>
            </div>
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("submitted")}
              <span className="text-sm">Enviada a DIAN</span>
            </div>
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("accepted")}
              <span className="text-sm">Aceptada por DIAN</span>
            </div>
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("rejected")}
              <span className="text-sm">Rechazada por DIAN</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
