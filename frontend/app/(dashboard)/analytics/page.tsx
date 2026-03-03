"use client";

import * as React from "react";
import {
  useAnalyticsDashboard,
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
import { RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { AIQueryBar, type AIQueryResponse } from "@/components/analytics/ai-query-bar";
import { AIResponseDisplay } from "@/components/analytics/ai-response-display";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCOP(cents: number): string {
  return (cents / 100).toLocaleString("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
  });
}

function GrowthBadge({ value }: { value: number }) {
  const isPositive = value >= 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-sm font-medium",
        isPositive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400",
      )}
    >
      {isPositive ? (
        <TrendingUp className="h-3.5 w-3.5" />
      ) : (
        <TrendingDown className="h-3.5 w-3.5" />
      )}
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}

const PERIOD_OPTIONS: { value: AnalyticsPeriod; label: string }[] = [
  { value: "today", label: "Hoy" },
  { value: "week", label: "Semana" },
  { value: "month", label: "Mes" },
  { value: "quarter", label: "Trimestre" },
  { value: "year", label: "Año" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsDashboardPage() {
  const [period, setPeriod] = React.useState<AnalyticsPeriod>("month");
  const [aiResponse, setAiResponse] = React.useState<AIQueryResponse | null>(null);
  const [aiLoading, setAiLoading] = React.useState(false);

  const { data, isLoading, isError } = useAnalyticsDashboard(period);

  const handleAIResponse = (response: AIQueryResponse) => {
    setAiLoading(false);
    setAiResponse(response);
  };

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
          No se pudieron cargar las analíticas. Intenta de nuevo más tarde.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* ─── AI Query Bar ──────────────────────────────────────────────────── */}
      <AIQueryBar
        onResponse={handleAIResponse}
        className="w-full"
      />
      <AIResponseDisplay
        response={aiResponse}
        isLoading={aiLoading}
      />

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

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Patients KPI */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pacientes</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold tabular-nums">
                {data.patients.total.toLocaleString("es-CO")}
              </span>
            </div>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              {data.patients.new_in_period} nuevos en el período
            </p>
            <div className="mt-1">
              <GrowthBadge value={data.patients.growth_percentage} />
            </div>
          </CardContent>
        </Card>

        {/* Appointments KPI */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Citas hoy</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold tabular-nums">
                {data.appointments.today_count}
              </span>
            </div>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              {data.appointments.period_total} en el período
            </p>
            <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
              Inasistencia:{" "}
              <span
                className={cn(
                  "font-medium",
                  data.appointments.no_show_rate > 15
                    ? "text-red-600 dark:text-red-400"
                    : "text-foreground",
                )}
              >
                {data.appointments.no_show_rate.toFixed(1)}%
              </span>
            </p>
          </CardContent>
        </Card>

        {/* Revenue KPI */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Ingresos recaudados</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums">
                {formatCOP(data.revenue.collected)}
              </span>
            </div>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              Pendiente: {formatCOP(data.revenue.pending_collection)}
            </p>
            <div className="mt-1">
              <GrowthBadge value={data.revenue.growth_percentage} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom row: Top procedures + Doctor occupancy */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Top Procedures */}
        <Card>
          <CardHeader>
            <CardTitle>Procedimientos más realizados</CardTitle>
            <CardDescription>Top 5 del período seleccionado</CardDescription>
          </CardHeader>
          <CardContent>
            {data.top_procedures.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
                Sin datos para el período seleccionado.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código CUPS</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right">Cantidad</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.top_procedures.slice(0, 5).map((proc) => (
                    <TableRow key={proc.cups_code}>
                      <TableCell className="font-mono text-xs">
                        {proc.cups_code}
                      </TableCell>
                      <TableCell className="text-sm">{proc.description}</TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {proc.count}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Doctor Occupancy */}
        <Card>
          <CardHeader>
            <CardTitle>Ocupación por doctor</CardTitle>
            <CardDescription>
              Citas completadas vs. programadas en el período
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.doctor_occupancy.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
                Sin datos para el período seleccionado.
              </p>
            ) : (
              <div className="space-y-4">
                {data.doctor_occupancy.map((doc) => (
                  <div key={doc.doctor_id} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium truncate max-w-[180px]">
                        {doc.doctor_name}
                      </span>
                      <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums shrink-0">
                        {doc.completed}/{doc.scheduled} —{" "}
                        <span className="font-semibold text-foreground">
                          {doc.occupancy_rate.toFixed(0)}%
                        </span>
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-[hsl(var(--muted))]">
                      <div
                        className={cn(
                          "h-2 rounded-full transition-all",
                          doc.occupancy_rate >= 80
                            ? "bg-green-500"
                            : doc.occupancy_rate >= 50
                              ? "bg-primary-500"
                              : "bg-yellow-500",
                        )}
                        style={{
                          width: `${Math.min(doc.occupancy_rate, 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
