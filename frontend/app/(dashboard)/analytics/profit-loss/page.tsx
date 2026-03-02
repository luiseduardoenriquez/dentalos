"use client";

import * as React from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableWrapper,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { formatCurrency, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PLByMethod {
  method: string;
  count: number;
  amount_cents: number;
}

interface PLByCategory {
  category_id: string;
  category_name: string;
  amount_cents: number;
  transaction_count: number;
}

interface ProfitLossData {
  date_from: string;
  date_to: string;
  total_revenue_cents: number;
  total_expenses_cents: number;
  net_profit_cents: number;
  profit_margin_percent: number;
  revenue_by_payment_method: PLByMethod[];
  expenses_by_category: PLByCategory[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Efectivo",
  card: "Tarjeta",
  transfer: "Transferencia",
  nequi: "Nequi",
  daviplata: "Daviplata",
  insurance: "Aseguradora",
  other: "Otro",
};

// ─── Metric Card ──────────────────────────────────────────────────────────────

function MetricCard({
  title,
  valueCents,
  icon: Icon,
  variant,
  subtitle,
}: {
  title: string;
  valueCents: number;
  icon: React.ComponentType<{ className?: string }>;
  variant: "income" | "expense" | "net";
  subtitle?: string;
}) {
  const variantStyles = {
    income: {
      card: "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-900/10",
      icon: "bg-green-100 dark:bg-green-900/30 text-green-600",
      value: "text-green-700 dark:text-green-400",
    },
    expense: {
      card: "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-900/10",
      icon: "bg-red-100 dark:bg-red-900/30 text-red-600",
      value: "text-red-700 dark:text-red-400",
    },
    net: {
      card:
        valueCents >= 0
          ? "border-primary-200 bg-primary-50/50 dark:border-primary-800 dark:bg-primary-900/10"
          : "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-900/10",
      icon:
        valueCents >= 0
          ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
          : "bg-red-100 dark:bg-red-900/30 text-red-600",
      value:
        valueCents >= 0
          ? "text-primary-700 dark:text-primary-400"
          : "text-red-700 dark:text-red-400",
    },
  };

  const styles = variantStyles[variant];

  return (
    <div className={cn("rounded-xl border p-5 transition-shadow hover:shadow-sm", styles.card)}>
      <div className="flex items-center gap-3 mb-3">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg shrink-0",
            styles.icon,
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
        <span className="text-sm text-[hsl(var(--muted-foreground))]">{title}</span>
      </div>
      <p className={cn("text-3xl font-bold tabular-nums", styles.value)}>
        {formatCurrency(Math.abs(valueCents), "COP")}
      </p>
      {subtitle && (
        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{subtitle}</p>
      )}
    </div>
  );
}

// ─── Horizontal Bar ───────────────────────────────────────────────────────────

function HorizontalBar({
  value,
  max,
  colorClass,
}: {
  value: number;
  max: number;
  colorClass: string;
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="relative h-2 w-full rounded-full bg-[hsl(var(--muted))] overflow-hidden">
      <div
        className={cn("absolute inset-y-0 left-0 rounded-full transition-all duration-300", colorClass)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProfitLossPage() {
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .split("T")[0];
  const today = now.toISOString().split("T")[0];

  const [dateFrom, setDateFrom] = React.useState(firstDay);
  const [dateTo, setDateTo] = React.useState(today);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["analytics", "profit-loss", dateFrom, dateTo],
    queryFn: () =>
      apiGet<ProfitLossData>("/analytics/profit-loss", {
        date_from: dateFrom,
        date_to: dateTo,
      }),
    staleTime: 60_000,
    enabled: Boolean(dateFrom && dateTo),
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
          No se pudieron cargar los datos de P&amp;G. Intenta de nuevo.
        </CardContent>
      </Card>
    );
  }

  const maxRevenue = Math.max(
    ...(data?.revenue_by_payment_method.map((m) => m.amount_cents) ?? [1]),
    1,
  );
  const maxExpense = Math.max(
    ...(data?.expenses_by_category.map((c) => c.amount_cents) ?? [1]),
    1,
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Date range filter */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1">
          <label
            htmlFor="pl-date-from"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Desde
          </label>
          <Input
            id="pl-date-from"
            type="date"
            className="w-36"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <label
            htmlFor="pl-date-to"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Hasta
          </label>
          <Input
            id="pl-date-to"
            type="date"
            className="w-36"
            max={today}
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
        {data && (
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            {data.date_from} — {data.date_to}
          </p>
        )}
      </div>

      {/* Top KPI cards */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <MetricCard
            title="Total ingresos"
            valueCents={data.total_revenue_cents}
            icon={TrendingDown}
            variant="income"
          />
          <MetricCard
            title="Total egresos"
            valueCents={data.total_expenses_cents}
            icon={TrendingUp}
            variant="expense"
          />
          <MetricCard
            title="Utilidad neta"
            valueCents={data.net_profit_cents}
            icon={Minus}
            variant="net"
            subtitle={
              data.profit_margin_percent !== undefined
                ? `Margen: ${data.profit_margin_percent.toFixed(1)}%`
                : undefined
            }
          />
        </div>
      )}

      {/* No data */}
      {!isLoading && !data && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
            No hay datos P&amp;G para el período seleccionado.
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <Separator />

          {/* Revenue breakdown by payment method */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Ingresos por método de pago</CardTitle>
                <CardDescription>
                  Distribución de pagos recibidos en el período
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.revenue_by_payment_method.length === 0 ? (
                  <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-6">
                    Sin datos de ingresos.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {data.revenue_by_payment_method.map((row) => (
                      <div key={row.method} className="space-y-1.5">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium text-foreground">
                            {PAYMENT_METHOD_LABELS[row.method] ?? row.method}
                          </span>
                          <div className="flex items-center gap-3 text-right">
                            <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums">
                              {row.count} transacc.
                            </span>
                            <span className="font-semibold tabular-nums text-green-700 dark:text-green-400">
                              {formatCurrency(row.amount_cents, "COP")}
                            </span>
                          </div>
                        </div>
                        <HorizontalBar
                          value={row.amount_cents}
                          max={maxRevenue}
                          colorClass="bg-green-500 dark:bg-green-600"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Expenses breakdown by category */}
            <Card>
              <CardHeader>
                <CardTitle>Egresos por categoría</CardTitle>
                <CardDescription>
                  Distribución de gastos registrados en el período
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.expenses_by_category.length === 0 ? (
                  <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-6">
                    Sin datos de egresos.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {data.expenses_by_category.map((row) => (
                      <div key={row.category_id} className="space-y-1.5">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium text-foreground">
                            {row.category_name}
                          </span>
                          <div className="flex items-center gap-3 text-right">
                            <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums">
                              {row.transaction_count} gasto{row.transaction_count !== 1 ? "s" : ""}
                            </span>
                            <span className="font-semibold tabular-nums text-red-600 dark:text-red-400">
                              {formatCurrency(row.amount_cents, "COP")}
                            </span>
                          </div>
                        </div>
                        <HorizontalBar
                          value={row.amount_cents}
                          max={maxExpense}
                          colorClass="bg-red-500 dark:bg-red-600"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Detail table — revenue vs expenses side by side */}
          <Card>
            <CardHeader>
              <CardTitle>Resumen comparativo</CardTitle>
              <CardDescription>
                Ingresos y egresos totales del período seleccionado
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <TableWrapper>
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead>Concepto</TableHead>
                      <TableHead className="text-right">Monto</TableHead>
                      <TableHead className="text-right">% del total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {/* Revenue row */}
                    <TableRow>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
                          <span className="text-sm font-medium text-foreground">
                            Ingresos
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-semibold text-green-700 dark:text-green-400">
                        {formatCurrency(data.total_revenue_cents, "COP")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-sm text-[hsl(var(--muted-foreground))]">
                        100%
                      </TableCell>
                    </TableRow>

                    {/* Expenses row */}
                    <TableRow>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" />
                          <span className="text-sm font-medium text-foreground">
                            Egresos
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-semibold text-red-600 dark:text-red-400">
                        {formatCurrency(data.total_expenses_cents, "COP")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-sm text-[hsl(var(--muted-foreground))]">
                        {data.total_revenue_cents > 0
                          ? `${((data.total_expenses_cents / data.total_revenue_cents) * 100).toFixed(1)}%`
                          : "—"}
                      </TableCell>
                    </TableRow>

                    {/* Net profit row */}
                    <TableRow className="border-t-2">
                      <TableCell>
                        <span className="text-sm font-bold text-foreground">
                          Utilidad neta
                        </span>
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right tabular-nums font-bold text-base",
                          data.net_profit_cents >= 0
                            ? "text-primary-700 dark:text-primary-400"
                            : "text-red-700 dark:text-red-400",
                        )}
                      >
                        {data.net_profit_cents < 0 && "−"}
                        {formatCurrency(Math.abs(data.net_profit_cents), "COP")}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right tabular-nums font-semibold text-sm",
                          data.profit_margin_percent >= 0
                            ? "text-primary-600"
                            : "text-red-600",
                        )}
                      >
                        {data.profit_margin_percent?.toFixed(1)}%
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableWrapper>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
