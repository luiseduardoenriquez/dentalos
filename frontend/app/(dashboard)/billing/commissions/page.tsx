"use client";

import * as React from "react";
import { BarChart3, Users, DollarSign, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { CommissionsBarChart } from "@/components/billing/commissions-bar-chart";
import { useCommissions } from "@/lib/hooks/use-commissions";
import { formatCurrency } from "@/lib/utils";

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function CommissionsSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-7 w-64" />
      <div className="flex gap-4">
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-10 w-40" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
      <Skeleton className="h-48 w-full rounded-xl" />
      <Skeleton className="h-48 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function CommissionsPage() {
  // Default: current month
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .split("T")[0];
  const today = now.toISOString().split("T")[0];

  const [dateFrom, setDateFrom] = React.useState(firstDay);
  const [dateTo, setDateTo] = React.useState(today);
  const [statusFilter, setStatusFilter] = React.useState<"paid" | "all">("paid");

  const { data, isLoading } = useCommissions({
    dateFrom,
    dateTo,
    status: statusFilter,
  });

  if (isLoading && !data) {
    return <CommissionsSkeleton />;
  }

  const commissions = data?.commissions ?? [];
  const totals = data?.totals ?? { total_revenue: 0, total_commission: 0 };
  const doctorCount = commissions.length;

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <BarChart3 className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">
          Comisiones por Doctor
        </h1>
      </div>

      {/* ─── Filters ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1">
          <label htmlFor="date-from" className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
            Desde
          </label>
          <Input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-40"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="date-to" className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
            Hasta
          </label>
          <Input
            id="date-to"
            type="date"
            value={dateTo}
            max={today}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-40"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
            Estado factura
          </label>
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as "paid" | "all")}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="paid">Solo pagadas</SelectItem>
              <SelectItem value="all">Todas</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* ─── KPI Cards ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-900/20">
                <DollarSign className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Ingreso total
                </p>
                <p className="text-xl font-bold tabular-nums text-foreground">
                  {formatCurrency(totals.total_revenue, "COP")}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50 text-green-600 dark:bg-green-900/20">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Total comisiones
                </p>
                <p className="text-xl font-bold tabular-nums text-foreground">
                  {formatCurrency(totals.total_commission, "COP")}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-900/20">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Doctores
                </p>
                <p className="text-xl font-bold tabular-nums text-foreground">
                  {doctorCount}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ─── Bar Chart ───────────────────────────────────────────────── */}
      {commissions.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Distribución de comisiones
            </CardTitle>
          </CardHeader>
          <CardContent>
            <CommissionsBarChart commissions={commissions} />
          </CardContent>
        </Card>
      )}

      {/* ─── Detail Table ────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">
            Detalle por doctor
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {commissions.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-10">
              No hay datos de comisiones para el período seleccionado.
            </p>
          ) : (
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Doctor</TableHead>
                    <TableHead>Especialidad</TableHead>
                    <TableHead className="text-right">Procedimientos</TableHead>
                    <TableHead className="text-right">Ingreso</TableHead>
                    <TableHead className="text-right">% Comisión</TableHead>
                    <TableHead className="text-right">Comisión</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {commissions.map((entry) => (
                    <TableRow key={entry.doctor.id}>
                      <TableCell>
                        <span className="text-sm font-medium text-foreground">
                          {entry.doctor.name}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-[hsl(var(--muted-foreground))]">
                          {entry.doctor.specialty || "—"}
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums">
                        {entry.procedure_count}
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums font-medium">
                        {formatCurrency(entry.total_revenue, "COP")}
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums">
                        {entry.commission_percentage}%
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums font-semibold text-green-600">
                        {formatCurrency(entry.commission_amount, "COP")}
                      </TableCell>
                    </TableRow>
                  ))}
                  {/* Totals row */}
                  <TableRow className="border-t-2 font-semibold">
                    <TableCell colSpan={3} className="text-sm">
                      Total
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {formatCurrency(totals.total_revenue, "COP")}
                    </TableCell>
                    <TableCell />
                    <TableCell className="text-right text-sm tabular-nums text-green-600">
                      {formatCurrency(totals.total_commission, "COP")}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableWrapper>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
