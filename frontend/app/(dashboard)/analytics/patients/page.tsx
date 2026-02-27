"use client";

import * as React from "react";
import {
  usePatientAnalytics,
  type AnalyticsPeriod,
  type DemographicBucket,
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

function getPercent(count: number, total: number): string {
  if (total === 0) return "0.0%";
  return ((count / total) * 100).toFixed(1) + "%";
}

// ─── Demographic List ─────────────────────────────────────────────────────────

function DemographicList({
  items,
  title,
  description,
}: {
  items: DemographicBucket[];
  title: string;
  description?: string;
}) {
  const total = items.reduce((s, b) => s + b.count, 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-[hsl(var(--muted-foreground))] py-2 text-center">
            Sin datos.
          </p>
        ) : (
          <ul className="divide-y divide-[hsl(var(--border))]">
            {items.map((b) => (
              <li
                key={b.label}
                className="flex items-center justify-between py-2"
              >
                <span className="text-sm font-medium">{b.label}</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums">
                    {getPercent(b.count, total)}
                  </span>
                  <span className="text-sm font-semibold tabular-nums w-10 text-right">
                    {b.count.toLocaleString("es-CO")}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientAnalyticsPage() {
  const [period, setPeriod] = React.useState<AnalyticsPeriod>("month");

  const { data, isLoading, isError } = usePatientAnalytics(period);

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
          No se pudieron cargar las analíticas de pacientes. Intenta de nuevo más tarde.
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

      {/* Active/Inactive + Retention summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pacientes activos</CardDescription>
          </CardHeader>
          <CardContent>
            <span className="text-4xl font-bold tabular-nums">
              {data.total_active.toLocaleString("es-CO")}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pacientes inactivos</CardDescription>
          </CardHeader>
          <CardContent>
            <span className="text-4xl font-bold tabular-nums text-[hsl(var(--muted-foreground))]">
              {data.total_inactive.toLocaleString("es-CO")}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Tasa de retención</CardDescription>
          </CardHeader>
          <CardContent>
            <span
              className={cn(
                "text-4xl font-bold tabular-nums",
                data.retention_rate >= 70
                  ? "text-green-600 dark:text-green-400"
                  : data.retention_rate >= 50
                    ? "text-yellow-600 dark:text-yellow-400"
                    : "text-red-600 dark:text-red-400",
              )}
            >
              {data.retention_rate.toFixed(1)}%
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Demographics */}
      <div className="grid gap-4 md:grid-cols-3">
        <DemographicList
          items={data.demographics_gender}
          title="Distribución por género"
        />
        <DemographicList
          items={data.demographics_age}
          title="Distribución por edad"
        />
        <DemographicList
          items={data.demographics_city}
          title="Top ciudades"
          description="Ciudades con más pacientes"
        />
      </div>

      {/* Acquisition trend */}
      <Card>
        <CardHeader>
          <CardTitle>Tendencia de adquisición</CardTitle>
          <CardDescription>Nuevos pacientes por fecha en el período</CardDescription>
        </CardHeader>
        <CardContent>
          {data.acquisition_trend.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
              Sin datos de adquisición para el período seleccionado.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Nuevos pacientes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.acquisition_trend.map((point) => (
                  <TableRow key={point.date}>
                    <TableCell className="tabular-nums text-sm">
                      {point.date}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium">
                      {point.count}
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
