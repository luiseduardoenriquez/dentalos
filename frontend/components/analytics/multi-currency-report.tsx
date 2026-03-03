"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DollarSign, TrendingUp, ArrowRightLeft } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CurrencyBreakdown {
  currency: string;
  total_revenue_cents: number;
  total_payments_cents: number;
  transaction_count: number;
  cop_equivalent_cents: number;
}

interface MultiCurrencyReportData {
  period: string;
  base_currency: string;
  breakdowns: CurrencyBreakdown[];
  total_cop_equivalent_cents: number;
}

const CURRENCY_LABELS: Record<string, string> = {
  COP: "Peso colombiano",
  USD: "Dólar estadounidense",
  MXN: "Peso mexicano",
  EUR: "Euro",
};

const CURRENCY_FLAGS: Record<string, string> = {
  COP: "🇨🇴",
  USD: "🇺🇸",
  MXN: "🇲🇽",
  EUR: "🇪🇺",
};

// ─── Component ────────────────────────────────────────────────────────────────

export function MultiCurrencyReport() {
  const [period, setPeriod] = React.useState("current_month");

  const { data, isLoading } = useQuery({
    queryKey: ["multi_currency_report", period],
    queryFn: () =>
      apiGet<MultiCurrencyReportData>(
        `/billing/reports/multi-currency?period=${period}`
      ),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-4">
              <Skeleton className="h-10 w-10 rounded-md" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-5 w-20" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  const breakdowns = data?.breakdowns ?? [];
  const totalCOP = data?.total_cop_equivalent_cents ?? 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <ArrowRightLeft className="h-4 w-4 text-primary-600" />
          Ingresos multi-moneda
        </CardTitle>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[160px] h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="current_month">Este mes</SelectItem>
            <SelectItem value="last_month">Mes anterior</SelectItem>
            <SelectItem value="current_quarter">Este trimestre</SelectItem>
            <SelectItem value="current_year">Este año</SelectItem>
          </SelectContent>
        </Select>
      </CardHeader>

      <CardContent className="space-y-4">
        {breakdowns.length === 0 ? (
          <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-6">
            No hay transacciones en múltiples monedas para este período.
          </p>
        ) : (
          <>
            {breakdowns.map((b) => (
              <div
                key={b.currency}
                className="flex items-center gap-4 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[hsl(var(--muted))] text-lg">
                  {CURRENCY_FLAGS[b.currency] ?? "💱"}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">
                    {CURRENCY_LABELS[b.currency] ?? b.currency}{" "}
                    <span className="text-[hsl(var(--muted-foreground))]">
                      ({b.currency})
                    </span>
                  </p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    {b.transaction_count} transacción
                    {b.transaction_count !== 1 ? "es" : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">
                    {formatCurrency(b.total_revenue_cents)}
                  </p>
                  {b.currency !== "COP" && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      ≈ {formatCurrency(b.cop_equivalent_cents)} COP
                    </p>
                  )}
                </div>
              </div>
            ))}

            {/* Total in COP */}
            <div className="flex items-center justify-between pt-3 border-t border-[hsl(var(--border))]">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary-600" />
                <span className="text-sm font-medium">
                  Total normalizado (COP)
                </span>
              </div>
              <span className="text-lg font-bold text-primary-600">
                {formatCurrency(totalCOP)}
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
