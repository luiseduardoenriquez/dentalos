"use client";

import * as React from "react";
import {
  useAppointmentAnalytics,
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

// Day-of-week labels (0 = Monday per ISO convention used in the backend)
const DAY_LABELS: Record<number, string> = {
  0: "Lun",
  1: "Mar",
  2: "Mié",
  3: "Jue",
  4: "Vie",
  5: "Sáb",
  6: "Dom",
};

function formatHourRange(hour: number): string {
  const start = hour.toString().padStart(2, "0") + ":00";
  const end = ((hour + 1) % 24).toString().padStart(2, "0") + ":00";
  return `${start}–${end}`;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AppointmentAnalyticsPage() {
  const [period, setPeriod] = React.useState<AnalyticsPeriod>("month");

  const { data, isLoading, isError } = useAppointmentAnalytics(period);

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
          No se pudieron cargar las analíticas de citas. Intenta de nuevo más tarde.
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

      {/* Average duration card */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Duración promedio de cita</CardDescription>
          </CardHeader>
          <CardContent>
            {data.average_duration_minutes !== null ? (
              <>
                <span className="text-4xl font-bold tabular-nums">
                  {Math.round(data.average_duration_minutes)}
                </span>
                <span className="ml-1 text-lg text-[hsl(var(--muted-foreground))]">min</span>
              </>
            ) : (
              <span className="text-[hsl(var(--muted-foreground))]">
                Sin datos suficientes
              </span>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Utilization table */}
      <Card>
        <CardHeader>
          <CardTitle>Utilización de agenda</CardTitle>
          <CardDescription>
            Citas programadas, completadas, canceladas e inasistencias por fecha
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.utilization.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
              Sin datos para el período seleccionado.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Programadas</TableHead>
                  <TableHead className="text-right">Completadas</TableHead>
                  <TableHead className="text-right">Canceladas</TableHead>
                  <TableHead className="text-right">Inasistencias</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.utilization.map((point) => (
                  <TableRow key={point.date}>
                    <TableCell className="tabular-nums text-sm">
                      {point.date}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {point.scheduled}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-green-600 dark:text-green-400 font-medium">
                      {point.completed}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-yellow-600 dark:text-yellow-400">
                      {point.cancelled}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-red-600 dark:text-red-400">
                      {point.no_show}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Peak hours + No-show trend side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Peak hours */}
        <Card>
          <CardHeader>
            <CardTitle>Horas pico</CardTitle>
            <CardDescription>
              Franjas horarias con mayor demanda de citas
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.peak_hours.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
                Sin datos de horas pico.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Hora</TableHead>
                    <TableHead>Día</TableHead>
                    <TableHead className="text-right">Citas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.peak_hours.map((ph, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono text-sm tabular-nums">
                        {formatHourRange(ph.hour)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {DAY_LABELS[ph.day_of_week] ?? ph.day_of_week}
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {ph.count}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* No-show trend */}
        <Card>
          <CardHeader>
            <CardTitle>Tendencia de inasistencias</CardTitle>
            <CardDescription>
              Tasa de inasistencia (%) por fecha en el período
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.no_show_trend.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] py-4 text-center">
                Sin datos de inasistencias.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Tasa inasistencia</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.no_show_trend.map((point) => (
                    <TableRow key={point.date}>
                      <TableCell className="tabular-nums text-sm">
                        {point.date}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right tabular-nums font-medium",
                          point.rate > 20
                            ? "text-red-600 dark:text-red-400"
                            : point.rate > 10
                              ? "text-yellow-600 dark:text-yellow-400"
                              : "text-foreground",
                        )}
                      >
                        {point.rate.toFixed(1)}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
