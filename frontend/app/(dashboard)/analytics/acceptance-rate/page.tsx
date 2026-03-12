"use client";

import * as React from "react";
import { RefreshCw, CheckCircle, Clock, XCircle, FileText, CalendarDays } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useAcceptanceRate } from "@/lib/hooks/use-analytics";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AcceptanceRatePage() {
  const [dateFrom, setDateFrom] = React.useState<string>("");
  const [dateTo, setDateTo] = React.useState<string>("");

  const { data, isLoading, isError } = useAcceptanceRate(
    dateFrom || undefined,
    dateTo || undefined,
  );

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
          No se pudieron cargar los datos de aceptación. Intenta de nuevo más tarde.
        </CardContent>
      </Card>
    );
  }

  // Backend returns rate as 0.0–1.0 ratio, convert to percentage for display
  const ratePct = data.acceptance_rate * 100;

  const rateColor =
    ratePct >= 70
      ? "text-green-600 dark:text-green-400"
      : ratePct >= 40
        ? "text-yellow-600 dark:text-yellow-400"
        : "text-red-600 dark:text-red-400";

  const rateBarColor =
    ratePct >= 70
      ? "bg-green-500"
      : ratePct >= 40
        ? "bg-yellow-500"
        : "bg-red-500";

  return (
    <div className="flex flex-col gap-6">
      {/* Date range filter */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1">
          <Label htmlFor="ar-date-from" className="text-xs">
            Desde
          </Label>
          <Input
            id="ar-date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-40"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="ar-date-to" className="text-xs">
            Hasta
          </Label>
          <Input
            id="ar-date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-40"
          />
        </div>
      </div>

      {/* Acceptance rate hero */}
      <Card>
        <CardHeader>
          <CardTitle>Tasa de aceptación</CardTitle>
          <CardDescription>
            Porcentaje de planes de tratamiento aceptados por los pacientes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-baseline gap-3">
            <span className={cn("text-5xl font-bold tabular-nums", rateColor)}>
              {ratePct.toFixed(1)}%
            </span>
            <span className="text-sm text-[hsl(var(--muted-foreground))]">
              de planes aceptados
            </span>
          </div>
          {/* Progress bar */}
          <div className="h-3 w-full rounded-full bg-[hsl(var(--muted))]">
            <div
              className={cn("h-3 rounded-full transition-all", rateBarColor)}
              style={{ width: `${Math.min(ratePct, 100)}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* KPI cards */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Total cotizaciones</p>
            </div>
            <p className="text-3xl font-bold tabular-nums text-foreground">
              {data.total_quotations.toLocaleString("es-CO")}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Aceptados</p>
            </div>
            <p className="text-3xl font-bold tabular-nums text-green-600 dark:text-green-400">
              {data.accepted_count.toLocaleString("es-CO")}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-4 w-4 text-yellow-500" />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Pendientes</p>
            </div>
            <p className="text-3xl font-bold tabular-nums text-yellow-600 dark:text-yellow-400">
              {data.pending_count.toLocaleString("es-CO")}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="h-4 w-4 text-red-500" />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Expirados</p>
            </div>
            <p className="text-3xl font-bold tabular-nums text-red-600 dark:text-red-400">
              {data.expired_count.toLocaleString("es-CO")}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              <CalendarDays className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Días promedio</p>
            </div>
            <p className="text-3xl font-bold tabular-nums text-foreground">
              {data.average_days_to_accept != null ? data.average_days_to_accept.toFixed(1) : "—"}
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
              para aceptar
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
