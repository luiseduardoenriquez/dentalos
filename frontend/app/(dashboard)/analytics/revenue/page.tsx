"use client";

import * as React from "react";
import {
  useRevenueAnalytics,
  type AnalyticsPeriod,
} from "@/lib/hooks/use-analytics";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const PERIOD_OPTIONS: { value: AnalyticsPeriod; label: string }[] = [
  { value: "today", label: "Hoy" },
  { value: "week", label: "Semana" },
  { value: "month", label: "Mes" },
  { value: "quarter", label: "Trimestre" },
  { value: "year", label: "Año" },
];

function formatCOP(cents: number): string {
  return (cents / 100).toLocaleString("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
  });
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Efectivo",
  card: "Tarjeta",
  transfer: "Transferencia",
  insurance: "Aseguradora",
  other: "Otro",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RevenueAnalyticsPage() {
  const [period, setPeriod] = React.useState<AnalyticsPeriod>("month");

  const { data, isLoading, isError } = useRevenueAnalytics(period);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-[hsl(var(--muted-foreground))]">
          No se pudieron cargar las analíticas de ingresos. Intenta de nuevo más tarde.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Period selector */}
      <div className="flex items-center gap-3">
        <label
          htmlFor="period-select"
          className="text-sm font-medium text-[hsl(var(--muted-foreground))]"
        >
          Período:
        </label>
        <select
          id="period-select"
          value={period}
          onChange={(e) => setPeriod(e.target.value as AnalyticsPeriod)}
          className={cn(
            "rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
            "px-3 py-1.5 text-sm text-foreground shadow-sm",
            "focus:outline-none focus:ring-2 focus:ring-primary-600",
          )}
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          {data.period.date_from} — {data.period.date_to}
        </span>
      </div>

      {/* Accounts receivable summary card */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Cartera pendiente (cuentas por cobrar)</CardDescription>
          </CardHeader>
          <CardContent>
            <span
              className={cn(
                "text-2xl font-bold tabular-nums",
                data.accounts_receivable > 0
                  ? "text-yellow-600 dark:text-yellow-400"
                  : "text-green-600 dark:text-green-400",
              )}
            >
              {formatCOP(data.accounts_receivable)}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Revenue trend */}
      <Card>
        <CardHeader>
          <CardTitle>Tendencia de ingresos</CardTitle>
          <CardDescription>Ingresos diarios recaudados en el período</CardDescription>
        </CardHeader>
        <CardContent>
          {data.trend.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
              Sin datos para el período seleccionado.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Ingresos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.trend.map((point) => (
                  <TableRow key={point.date}>
                    <TableCell className="tabular-nums text-sm">
                      {point.date}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium">
                      {formatCOP(point.amount)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* By doctor + By procedure */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* By doctor */}
        <Card>
          <CardHeader>
            <CardTitle>Ingresos por doctor</CardTitle>
            <CardDescription>
              Total recaudado por profesional en el período
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.by_doctor.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
                Sin datos.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Doctor</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.by_doctor.map((d) => (
                    <TableRow key={d.doctor_id}>
                      <TableCell className="font-medium text-sm">
                        {d.doctor_name}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatCOP(d.amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* By procedure */}
        <Card>
          <CardHeader>
            <CardTitle>Ingresos por procedimiento</CardTitle>
            <CardDescription>
              Procedimientos más rentables del período
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.by_procedure.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
                Sin datos.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>CUPS</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right">Cant.</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.by_procedure.map((p) => (
                    <TableRow key={p.cups_code}>
                      <TableCell className="font-mono text-xs">
                        {p.cups_code}
                      </TableCell>
                      <TableCell className="text-sm max-w-[140px] truncate">
                        {p.description}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {p.count}
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {formatCOP(p.amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Payment methods */}
      <Card>
        <CardHeader>
          <CardTitle>Métodos de pago</CardTitle>
          <CardDescription>
            Distribución de pagos por canal en el período
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.payment_methods.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
              Sin datos de métodos de pago.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Método</TableHead>
                  <TableHead className="text-right">Transacciones</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.payment_methods.map((pm) => (
                  <TableRow key={pm.method}>
                    <TableCell className="font-medium text-sm">
                      {PAYMENT_METHOD_LABELS[pm.method] ?? pm.method}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {pm.count}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium">
                      {formatCOP(pm.amount)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
