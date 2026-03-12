"use client";

/**
 * Revenue Dashboard page — SA-R01.
 *
 * Displays platform-wide revenue KPIs and trends:
 * 1. KPI cards: MRR, ARPA, LTV, NRR.
 * 2. MRR trend line chart (12-month rolling window).
 * 3. Two-column grid: plan breakdown pie chart + revenue by country bar chart.
 * 4. Active tenants stacked bar chart (active + new per month).
 *
 * Data source: useRevenueDashboard (GET /admin/analytics/revenue?months=12).
 * Stale time: 5 minutes. All monetary values stored as integer cents.
 */

import * as React from "react";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  BarChart2,
  RefreshCw,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  useRevenueDashboard,
  type RevenueKPIs,
  type RevenueMonthDataPoint,
  type RevenuePlanBreakdown,
  type RevenueCountryBreakdown,
} from "@/lib/hooks/use-admin";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Recharts pie slice colors — indigo, cyan, emerald, amber. */
const PIE_COLORS = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b"];

/** Indigo shades for bar charts. */
const BAR_COLOR_ACTIVE = "#6366f1";
const BAR_COLOR_NEW = "#a5b4fc";

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Format integer cents to a USD dollar string with $ prefix and commas.
 * Example: 150000 → "$1,500"
 */
const formatUSD = (cents: number): string =>
  "$" +
  (cents / 100).toLocaleString("en-US", { minimumFractionDigits: 0 });

/** Format a percentage with one decimal place. */
function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

/** Shorten large dollar amounts for chart Y-axis labels. */
function shortUSD(cents: number): string {
  const dollars = cents / 100;
  if (dollars >= 1_000_000) return `$${(dollars / 1_000_000).toFixed(1)}M`;
  if (dollars >= 1_000) return `$${(dollars / 1_000).toFixed(0)}K`;
  return `$${dollars.toFixed(0)}`;
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function RevenueSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {/* KPI cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-28" />
            </CardHeader>
            <CardContent className="space-y-2">
              <Skeleton className="h-9 w-32" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* MRR trend skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-56 mt-1" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-56 w-full rounded-lg" />
        </CardContent>
      </Card>

      {/* Two-column skeleton */}
      <div className="grid gap-6 lg:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-36" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-48 w-full rounded-lg" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Active tenants trend skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-44" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full rounded-lg" />
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

interface ErrorStateProps {
  onRetry: () => void;
}

function ErrorState({ onRetry }: ErrorStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-14 text-center">
        <BarChart2 className="h-10 w-10 text-muted-foreground opacity-40" />
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">
            No se pudo cargar el panel de ingresos
          </p>
          <p className="text-sm text-muted-foreground">
            Verifica la conexion con la API e intenta de nuevo.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="gap-2"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  growthBadge?: React.ReactNode;
}

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  growthBadge,
}: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardDescription className="text-sm font-medium">
            {title}
          </CardDescription>
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 shrink-0">
            <Icon className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-1">
        <p className="text-3xl font-bold tabular-nums tracking-tight text-foreground">
          {value}
        </p>
        {growthBadge && <div>{growthBadge}</div>}
        {subtitle && !growthBadge && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Growth Badge ─────────────────────────────────────────────────────────────

interface GrowthBadgeProps {
  pct: number;
  label?: string;
}

function GrowthBadge({ pct, label }: GrowthBadgeProps) {
  const isPositive = pct >= 0;
  return (
    <Badge
      variant={isPositive ? "success" : "destructive"}
      className="gap-1 text-xs"
    >
      {isPositive ? (
        <TrendingUp className="h-3 w-3" />
      ) : (
        <TrendingDown className="h-3 w-3" />
      )}
      {isPositive ? "+" : ""}
      {formatPct(pct)}
      {label ? ` ${label}` : ""}
    </Badge>
  );
}

// ─── MRR Trend Chart ──────────────────────────────────────────────────────────

interface MrrTrendChartProps {
  data: RevenueMonthDataPoint[];
}

function MrrTrendChart({ data }: MrrTrendChartProps) {
  if (data.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        Sin datos de tendencia disponibles.
      </p>
    );
  }

  // Convert cents to dollars for display.
  const chartData = data.map((d) => ({
    month: d.month,
    mrr: d.mrr_cents / 100,
    mrr_cents: d.mrr_cents,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart
        data={chartData}
        margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => shortUSD(v * 100)}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip
          formatter={(value: number) => [formatUSD(value * 100), "MRR"]}
          labelFormatter={(label: string) => `Mes: ${label}`}
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--popover))",
            color: "hsl(var(--popover-foreground))",
          }}
        />
        <Line
          type="monotone"
          dataKey="mrr"
          stroke="#4f46e5"
          strokeWidth={2}
          dot={{ r: 3, fill: "#4f46e5", strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ─── Plan Breakdown Pie Chart ─────────────────────────────────────────────────

interface PlanBreakdownChartProps {
  data: RevenuePlanBreakdown[];
}

function PlanBreakdownChart({ data }: PlanBreakdownChartProps) {
  if (data.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        Sin datos de planes disponibles.
      </p>
    );
  }

  const chartData = data.map((d) => ({
    name: d.plan_name,
    value: d.mrr_cents / 100,
    mrr_cents: d.mrr_cents,
    tenant_count: d.tenant_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={80}
          innerRadius={40}
          paddingAngle={3}
        >
          {chartData.map((_, index) => (
            <Cell
              key={`cell-${index}`}
              fill={PIE_COLORS[index % PIE_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string) => [
            formatUSD(value * 100),
            name,
          ]}
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--popover))",
            color: "hsl(var(--popover-foreground))",
          }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

// ─── Revenue by Country Bar Chart ─────────────────────────────────────────────

interface CountryBarChartProps {
  data: RevenueCountryBreakdown[];
}

function CountryBarChart({ data }: CountryBarChartProps) {
  if (data.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        Sin datos por pais disponibles.
      </p>
    );
  }

  const chartData = [...data]
    .sort((a, b) => b.mrr_cents - a.mrr_cents)
    .map((d) => ({
      country: d.country,
      mrr: d.mrr_cents / 100,
      mrr_cents: d.mrr_cents,
    }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={chartData}
        margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          vertical={false}
        />
        <XAxis
          dataKey="country"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => shortUSD(v * 100)}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip
          formatter={(value: number) => [formatUSD(value * 100), "MRR"]}
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--popover))",
            color: "hsl(var(--popover-foreground))",
          }}
        />
        <Bar dataKey="mrr" fill={BAR_COLOR_ACTIVE} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Active Tenants Stacked Bar Chart ─────────────────────────────────────────

interface ActiveTenantsTrendChartProps {
  data: RevenueMonthDataPoint[];
}

function ActiveTenantsTrendChart({ data }: ActiveTenantsTrendChartProps) {
  if (data.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        Sin datos de clinicas activas disponibles.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          vertical={false}
        />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--popover))",
            color: "hsl(var(--popover-foreground))",
          }}
        />
        <Legend
          iconType="square"
          iconSize={8}
          wrapperStyle={{ fontSize: 12 }}
        />
        <Bar
          dataKey="active_tenants"
          name="Activas"
          stackId="tenants"
          fill={BAR_COLOR_ACTIVE}
        />
        <Bar
          dataKey="new_tenants"
          name="Nuevas"
          stackId="tenants"
          fill={BAR_COLOR_NEW}
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── KPI Cards Section ────────────────────────────────────────────────────────

interface KpisSectionProps {
  kpis: RevenueKPIs;
}

function KpisSection({ kpis }: KpisSectionProps) {
  const nrrIsHigh = kpis.nrr_pct >= 100;

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {/* MRR Actual */}
      <KpiCard
        title="MRR Actual"
        value={formatUSD(kpis.current_mrr_cents)}
        icon={DollarSign}
        growthBadge={
          <GrowthBadge
            pct={kpis.mrr_growth_pct}
            label="vs mes anterior"
          />
        }
      />

      {/* ARPA */}
      <KpiCard
        title="ARPA"
        value={formatUSD(kpis.arpa_cents)}
        subtitle="Ingreso promedio por cuenta"
        icon={BarChart2}
      />

      {/* LTV Estimado */}
      <KpiCard
        title="LTV Estimado"
        value={formatUSD(kpis.ltv_cents)}
        subtitle="Valor de vida del cliente"
        icon={TrendingUp}
      />

      {/* NRR */}
      <KpiCard
        title="NRR"
        value={formatPct(kpis.nrr_pct)}
        icon={Users}
        growthBadge={
          <Badge
            variant={nrrIsHigh ? "success" : "warning"}
            className="text-xs"
          >
            {nrrIsHigh ? "Saludable ≥ 100%" : "Por debajo de 100%"}
          </Badge>
        }
      />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminRevenuePage() {
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useRevenueDashboard(12);

  // Show a toast on error so admins are notified even if they miss the inline error card.
  React.useEffect(() => {
    if (isError) {
      toast.error("Error al cargar el panel de ingresos", {
        description: "No se pudo obtener datos de /admin/analytics/revenue.",
      });
    }
  }, [isError]);

  return (
    <div className="flex flex-col gap-6">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Panel de ingresos
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          MRR, ARPA, LTV, NRR y tendencias de los ultimos 12 meses. Datos con un retraso maximo de 5 minutos.
        </p>
      </div>

      {/* ── Loading state ── */}
      {isLoading && <RevenueSkeleton />}

      {/* ── Error state ── */}
      {isError && !isLoading && (
        <ErrorState onRetry={() => refetch()} />
      )}

      {/* ── Content ── */}
      {!isLoading && !isError && data && (
        <>
          {/* 1. KPI Cards */}
          <KpisSection kpis={data.kpis} />

          {/* 2. MRR Trend */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">
                Tendencia de MRR
              </CardTitle>
              <CardDescription>
                Ingresos recurrentes mensuales — ultimos 12 meses
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MrrTrendChart data={data.monthly_trend} />
            </CardContent>
          </Card>

          {/* 3. Two-column: plan breakdown + country breakdown */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">
                  MRR por plan
                </CardTitle>
                <CardDescription>
                  Distribucion de ingresos segun el plan contratado
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PlanBreakdownChart data={data.plan_breakdown} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">
                  MRR por pais
                </CardTitle>
                <CardDescription>
                  Ingresos recurrentes mensuales por pais de origen
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CountryBarChart data={data.country_breakdown} />
              </CardContent>
            </Card>
          </div>

          {/* 4. Active tenants trend */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">
                Clinicas activas por mes
              </CardTitle>
              <CardDescription>
                Clinicas activas y nuevas por periodo — ultimos 12 meses
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ActiveTenantsTrendChart data={data.monthly_trend} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
