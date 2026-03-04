"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CreditCard,
  TrendingUp,
  CheckCircle2,
  Users,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { apiGet } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FinancingStatusBadge } from "@/components/billing/financing-status-badge";
import { formatCurrency, formatDate } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ProviderBreakdown {
  provider: string;
  count: number;
  total_amount_cents: number;
  approval_rate: number;
}

interface StatusBreakdown {
  status: string;
  count: number;
  total_amount_cents: number;
}

interface FinancingReport {
  total_applications: number;
  total_amount_cents: number;
  approved_count: number;
  approval_rate: number;
  by_provider: ProviderBreakdown[];
  by_status: StatusBreakdown[];
}

interface FinancingApplication {
  id: string;
  invoice_id: string;
  patient_name: string;
  provider: string;
  installments: number;
  amount_cents: number;
  status: string;
  created_at: string;
}

interface ApplicationListResponse {
  items: FinancingApplication[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Provider labels ──────────────────────────────────────────────────────────

const PROVIDER_LABELS: Record<string, string> = {
  addi: "Addi",
  sistecredito: "Sistecrédito",
  mercadopago: "Mercado Pago",
};

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
      <div className="h-64 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function FinancingPage() {
  const [page, setPage] = React.useState(1);
  const pageSize = 10;

  const {
    data: report,
    isLoading: isLoadingReport,
    isError: isReportError,
    refetch: refetchReport,
  } = useQuery({
    queryKey: ["financing-report"],
    queryFn: () => apiGet<FinancingReport>("/financing/report"),
    staleTime: 2 * 60_000,
  });

  const {
    data: applicationsData,
    isLoading: isLoadingApps,
  } = useQuery({
    queryKey: ["financing-applications", page, pageSize],
    queryFn: () =>
      apiGet<ApplicationListResponse>(
        `/financing/applications?page=${page}&page_size=${pageSize}`,
      ),
    staleTime: 60_000,
  });

  const isLoading = isLoadingReport || isLoadingApps;

  if (isLoading) return <PageSkeleton />;

  if (isReportError || !report) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          No se pudo cargar el reporte de financiamiento.
        </p>
        <Button variant="outline" size="sm" onClick={() => refetchReport()}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    );
  }

  const applications = applicationsData?.items ?? [];
  const totalPages = applicationsData ? Math.ceil(applicationsData.total / pageSize) : 1;

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Financiamiento de Pacientes
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Monitorea las solicitudes de financiamiento y su estado.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetchReport()}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Actualizar
        </Button>
      </div>

      {/* ─── Summary cards ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" />
              Total solicitudes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums text-foreground">
              {report.total_applications.toLocaleString("es-CO")}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              Acumulado total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <CreditCard className="h-3.5 w-3.5" />
              Monto total
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums text-foreground">
              {formatCurrency(report.total_amount_cents, "COP")}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              En todas las solicitudes
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Aprobadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums text-foreground">
              {report.approved_count.toLocaleString("es-CO")}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              Solicitudes aprobadas
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" />
              Tasa de aprobación
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums text-green-600 dark:text-green-400">
              {report.approval_rate.toFixed(0)}%
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              Del total de solicitudes
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ─── By provider ─────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Por proveedor</CardTitle>
          <CardDescription>
            Distribución de solicitudes por entidad financiadora.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {report.by_provider.length === 0 ? (
            <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              Sin datos de proveedores todavía.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Proveedor</TableHead>
                  <TableHead className="text-right">Solicitudes</TableHead>
                  <TableHead className="text-right">Monto total</TableHead>
                  <TableHead className="text-right">Aprobación</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.by_provider.map((row) => (
                  <TableRow key={row.provider}>
                    <TableCell className="font-medium text-foreground">
                      {PROVIDER_LABELS[row.provider] ?? row.provider}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {row.count.toLocaleString("es-CO")}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(row.total_amount_cents, "COP")}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <span
                        className={
                          row.approval_rate >= 70
                            ? "text-green-600 dark:text-green-400 font-medium"
                            : row.approval_rate >= 40
                            ? "text-yellow-600 dark:text-yellow-400 font-medium"
                            : "text-red-600 dark:text-red-400 font-medium"
                        }
                      >
                        {row.approval_rate.toFixed(0)}%
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ─── By status ───────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Por estado</CardTitle>
          <CardDescription>
            Distribución de solicitudes según su estado actual.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {report.by_status.length === 0 ? (
            <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              Sin datos de estados todavía.
            </p>
          ) : (
            <div className="space-y-3">
              {report.by_status.map((row) => {
                const pct =
                  report.total_applications > 0
                    ? (row.count / report.total_applications) * 100
                    : 0;
                return (
                  <div key={row.status} className="flex items-center gap-3">
                    <div className="w-28 shrink-0">
                      <FinancingStatusBadge status={row.status} />
                    </div>
                    <div className="flex-1 h-2.5 rounded-full bg-slate-100 dark:bg-zinc-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary-600 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="w-16 text-right text-sm tabular-nums text-foreground shrink-0">
                      {row.count.toLocaleString("es-CO")}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ─── Recent applications ─────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Solicitudes recientes</CardTitle>
          <CardDescription>
            Últimas solicitudes de financiamiento registradas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {applications.length === 0 ? (
            <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No hay solicitudes registradas todavía.
            </p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Paciente</TableHead>
                    <TableHead>Proveedor</TableHead>
                    <TableHead className="text-right">Monto</TableHead>
                    <TableHead className="text-center">Cuotas</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {applications.map((app) => (
                    <TableRow key={app.id}>
                      <TableCell className="font-medium text-foreground">
                        {app.patient_name}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {PROVIDER_LABELS[app.provider] ?? app.provider}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-sm">
                        {formatCurrency(app.amount_cents, "COP")}
                      </TableCell>
                      <TableCell className="text-center tabular-nums text-sm">
                        {app.installments}x
                      </TableCell>
                      <TableCell>
                        <FinancingStatusBadge status={app.status} />
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                        {formatDate(app.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Anterior
                  </Button>
                  <span className="text-sm text-[hsl(var(--muted-foreground))]">
                    Página {page} de {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Siguiente
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
