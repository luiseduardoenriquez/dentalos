"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, MessageSquare, Users, RefreshCw, AlertCircle } from "lucide-react";
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
import { NpsChart } from "@/components/analytics/nps-chart";
import { DetractorInbox } from "@/components/analytics/detractor-inbox";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type DateRange = "7d" | "30d" | "90d";

interface NpsTrendPoint {
  period: string;
  nps_score: number;
  responses: number;
}

interface NpsDashboard {
  nps_score: number;
  total_responses: number;
  promoters_count: number;
  passives_count: number;
  detractors_count: number;
  response_rate: number;
  trend: NpsTrendPoint[];
}

interface DoctorNpsRow {
  doctor_id: string;
  doctor_name: string;
  nps_score: number;
  total_responses: number;
  promoters: number;
  detractors: number;
}

interface DoctorNpsList {
  items: DoctorNpsRow[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function npsScoreColor(score: number): string {
  if (score > 30) return "text-green-600 dark:text-green-400";
  if (score >= 0) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

function npsScoreLabel(score: number): string {
  if (score > 50) return "Excelente";
  if (score > 30) return "Bueno";
  if (score >= 0) return "Necesita mejorar";
  return "Crítico";
}

// ─── Date range filter ────────────────────────────────────────────────────────

const DATE_RANGES: Array<{ value: DateRange; label: string }> = [
  { value: "7d", label: "Últimos 7 días" },
  { value: "30d", label: "Últimos 30 días" },
  { value: "90d", label: "Últimos 90 días" },
];

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-xl bg-slate-100 dark:bg-zinc-800" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-slate-100 dark:bg-zinc-800" />
      <div className="h-64 rounded-xl bg-slate-100 dark:bg-zinc-800" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NpsDashboardPage() {
  const [dateRange, setDateRange] = React.useState<DateRange>("30d");

  const {
    data: npsData,
    isLoading: isLoadingNps,
    isError: isNpsError,
    refetch: refetchNps,
  } = useQuery({
    queryKey: ["analytics-nps", dateRange],
    queryFn: () =>
      apiGet<NpsDashboard>(`/analytics/nps?range=${dateRange}`),
    staleTime: 5 * 60_000,
  });

  const {
    data: byDoctorData,
    isLoading: isLoadingDoctor,
  } = useQuery({
    queryKey: ["analytics-nps-by-doctor", dateRange],
    queryFn: () =>
      apiGet<DoctorNpsList>(`/analytics/nps/by-doctor?range=${dateRange}`),
    staleTime: 5 * 60_000,
  });

  const isLoading = isLoadingNps || isLoadingDoctor;

  if (isLoading) return <PageSkeleton />;

  if (isNpsError || !npsData) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          No se pudo cargar el panel de NPS.
        </p>
        <Button variant="outline" size="sm" onClick={() => refetchNps()}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    );
  }

  const promotersCount = npsData.promoters_count ?? 0;
  const passivesCount = npsData.passives_count ?? 0;
  const detractorsCount = npsData.detractors_count ?? 0;
  const totalResponded = promotersCount + passivesCount + detractorsCount;
  const doctors = byDoctorData?.items ?? [];

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            NPS &amp; Satisfacción
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Mide la lealtad y satisfacción de tus pacientes.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetchNps()}
          disabled={isLoading}
        >
          <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isLoading && "animate-spin")} />
          Actualizar
        </Button>
      </div>

      {/* ─── Date range filter ────────────────────────────────────────────── */}
      <div className="flex gap-1.5 flex-wrap">
        {DATE_RANGES.map((r) => (
          <button
            key={r.value}
            type="button"
            onClick={() => setDateRange(r.value)}
            className={cn(
              "rounded-full px-3 py-1 text-sm font-medium transition-colors",
              dateRange === r.value
                ? "bg-primary-600 text-white"
                : "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))]/80",
            )}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* ─── Big NPS score + summary cards ───────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {/* NPS Score — big display */}
        <Card className="md:col-span-1">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" />
              NPS Score
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p
              className={cn(
                "text-5xl font-bold tabular-nums",
                npsScoreColor(npsData.nps_score),
              )}
            >
              {npsData.nps_score > 0 ? "+" : ""}
              {npsData.nps_score}
            </p>
            <p
              className={cn(
                "mt-1 text-xs font-medium",
                npsScoreColor(npsData.nps_score),
              )}
            >
              {npsScoreLabel(npsData.nps_score)}
            </p>
          </CardContent>
        </Card>

        {/* Total responses */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5" />
              Respuestas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold tabular-nums text-foreground">
              {(npsData.total_responses ?? 0).toLocaleString("es-CO")}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              Tasa: {(npsData.response_rate ?? 0).toFixed(0)}%
            </p>
          </CardContent>
        </Card>

        {/* Promoters */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5 text-green-500" />
              Promotores (9-10)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold tabular-nums text-green-600 dark:text-green-400">
              {promotersCount.toLocaleString("es-CO")}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              {totalResponded > 0
                ? `${((promotersCount / totalResponded) * 100).toFixed(0)}% del total`
                : "—"}
            </p>
          </CardContent>
        </Card>

        {/* Detractors */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5 text-red-500" />
              Detractores (0-6)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold tabular-nums text-red-600 dark:text-red-400">
              {detractorsCount.toLocaleString("es-CO")}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              {totalResponded > 0
                ? `${((detractorsCount / totalResponded) * 100).toFixed(0)}% del total`
                : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ─── NPS Distribution ────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Distribución NPS</CardTitle>
          <CardDescription>
            Promotores · Pasivos · Detractores
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Distribution bars */}
          <div className="space-y-3">
            {[
              {
                label: "Promotores",
                count: promotersCount,
                colorBar: "bg-green-500",
                colorText: "text-green-600 dark:text-green-400",
              },
              {
                label: "Pasivos",
                count: passivesCount,
                colorBar: "bg-yellow-400",
                colorText: "text-yellow-600 dark:text-yellow-400",
              },
              {
                label: "Detractores",
                count: detractorsCount,
                colorBar: "bg-red-500",
                colorText: "text-red-600 dark:text-red-400",
              },
            ].map((row) => (
              <div key={row.label} className="flex items-center gap-3">
                <span className={cn("w-24 text-sm font-medium shrink-0", row.colorText)}>
                  {row.label}
                </span>
                <div className="flex-1 h-3 rounded-full bg-slate-100 dark:bg-zinc-800 overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", row.colorBar)}
                    style={{
                      width:
                        totalResponded > 0
                          ? `${(row.count / totalResponded) * 100}%`
                          : "0%",
                    }}
                  />
                </div>
                <span className="w-8 text-right text-sm font-medium tabular-nums text-foreground shrink-0">
                  {row.count}
                </span>
              </div>
            ))}
          </div>

          {/* Trend chart */}
          {(npsData.trend ?? []).length > 0 && (
            <div className="mt-4 pt-4 border-t border-[hsl(var(--border))]">
              <p className="text-sm font-medium text-foreground mb-3">Tendencia mensual</p>
              <NpsChart trend={npsData.trend} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* ─── By doctor ───────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>NPS por doctor</CardTitle>
          <CardDescription>
            Satisfacción desglosada por profesional.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {doctors.length === 0 ? (
            <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              Sin datos de satisfacción por doctor todavía.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Doctor</TableHead>
                  <TableHead className="text-center">NPS</TableHead>
                  <TableHead className="text-right">Respuestas</TableHead>
                  <TableHead className="text-right">Promotores</TableHead>
                  <TableHead className="text-right">Detractores</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {doctors.map((row) => (
                  <TableRow key={row.doctor_id}>
                    <TableCell className="font-medium text-foreground">
                      {row.doctor_name}
                    </TableCell>
                    <TableCell className="text-center">
                      <span
                        className={cn(
                          "text-sm font-bold tabular-nums",
                          npsScoreColor(row.nps_score),
                        )}
                      >
                        {row.nps_score > 0 ? "+" : ""}
                        {row.nps_score}
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      {row.total_responses}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm text-green-600 dark:text-green-400">
                      {row.promoters}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm text-red-600 dark:text-red-400">
                      {row.detractors}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ─── Detractor inbox ─────────────────────────────────────────────── */}
      <DetractorInbox />
    </div>
  );
}
