"use client";

import * as React from "react";
import { useAdminAnalytics, type PlatformAnalyticsResponse } from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function formatNumber(value: number): string {
  return value.toLocaleString("es-CO");
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: React.ReactNode;
  valueClassName?: string;
  className?: string;
}

function KpiCard({ title, value, subtitle, valueClassName, className }: KpiCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
      </CardHeader>
      <CardContent>
        <p
          className={cn(
            "text-3xl font-bold tabular-nums tracking-tight",
            valueClassName,
          )}
        >
          {value}
        </p>
        {subtitle && (
          <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
            {subtitle}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function AnalyticsLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {/* KPI skeletons */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-9 w-28" />
              <Skeleton className="h-3 w-40 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Extra metric card skeletons */}
      <div className="grid gap-4 sm:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-36" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-9 w-24" />
              <Skeleton className="h-3 w-32 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Churn Rate Card ──────────────────────────────────────────────────────────

interface ChurnRateCardProps {
  churn_rate: number;
}

function ChurnRateCard({ churn_rate }: ChurnRateCardProps) {
  const isLow = churn_rate < 5;
  const isMedium = churn_rate >= 5 && churn_rate <= 10;
  const isHigh = churn_rate > 10;

  return (
    <Card
      className={cn(
        "border",
        isHigh
          ? "border-red-200 bg-red-50/50 dark:border-red-700/40 dark:bg-red-900/10"
          : isMedium
            ? "border-amber-200 bg-amber-50/50 dark:border-amber-700/40 dark:bg-amber-900/10"
            : "border-green-200 bg-green-50/50 dark:border-green-700/40 dark:bg-green-900/10",
      )}
    >
      <CardHeader className="pb-2">
        <CardDescription>Tasa de cancelacion (churn)</CardDescription>
      </CardHeader>
      <CardContent>
        <p
          className={cn(
            "text-3xl font-bold tabular-nums tracking-tight",
            isHigh
              ? "text-red-700 dark:text-red-300"
              : isMedium
                ? "text-amber-700 dark:text-amber-300"
                : "text-green-700 dark:text-green-300",
          )}
        >
          {formatPercent(churn_rate)}
        </p>
        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
          {isLow
            ? "Saludable — por debajo del 5%"
            : isMedium
              ? "Moderado — entre 5% y 10%"
              : "Critico — por encima del 10%"}
        </p>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminAnalyticsPage() {
  const { data: analytics, isLoading, isError, refetch } = useAdminAnalytics();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Analitica de plataforma
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Metricas globales de uso, ingresos y crecimiento.
          </p>
        </div>
        <AnalyticsLoadingSkeleton />
      </div>
    );
  }

  if (isError || !analytics) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Analitica de plataforma
          </h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar las analiticas. Verifica la conexion con la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const arrCents = analytics.mrr_cents * 12;
  const avgRevenuePerClinic =
    analytics.active_tenants > 0
      ? Math.round(analytics.mrr_cents / analytics.active_tenants)
      : 0;

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Analitica de plataforma
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Metricas globales de uso, ingresos y crecimiento. Datos con un retraso
          maximo de 5 minutos.
        </p>
      </div>

      {/* Main KPI grid — 6 cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          title="Total clinicas"
          value={formatNumber(analytics.total_tenants)}
          subtitle={`${formatNumber(analytics.active_tenants)} activas`}
        />

        <KpiCard
          title="Ingresos mensuales (MRR)"
          value={formatUSD(analytics.mrr_cents)}
          subtitle="Recurrente mensual"
        />

        <KpiCard
          title="Ingresos anuales (ARR)"
          value={formatUSD(arrCents)}
          subtitle="Proyeccion anual"
        />

        <KpiCard
          title="Usuarios totales"
          value={formatNumber(analytics.total_users)}
          subtitle="En toda la plataforma"
        />

        <KpiCard
          title="Total pacientes"
          value={formatNumber(analytics.total_patients)}
          subtitle="En toda la plataforma"
        />

        <KpiCard
          title="Usuarios activos mensuales (MAU)"
          value={formatNumber(analytics.mau)}
          subtitle="Usuarios activos mensuales"
        />
      </div>

      {/* Secondary metrics */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Churn rate card with color coding */}
        <ChurnRateCard churn_rate={analytics.churn_rate} />

        {/* Average revenue per clinic */}
        <Card className="border-dashed">
          <CardHeader className="pb-2">
            <CardDescription>Ingresos por clinica (promedio)</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums tracking-tight">
              {analytics.active_tenants > 0 ? formatUSD(avgRevenuePerClinic) : "—"}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              MRR / clinicas activas
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
