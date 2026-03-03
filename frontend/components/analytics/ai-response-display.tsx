"use client";

import * as React from "react";
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
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sparkles,
  BarChart2,
  TrendingUp,
  PieChart,
  Table2,
  Hash,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AIQueryResponse } from "@/components/analytics/ai-query-bar";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIResponseDisplayProps {
  response: AIQueryResponse | null;
  isLoading: boolean;
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CHART_TYPE_CONFIG: Record<
  AIQueryResponse["chart_type"],
  { label: string; Icon: React.ElementType; color: string }
> = {
  bar: {
    label: "Barras",
    Icon: BarChart2,
    color: "text-blue-600 dark:text-blue-400",
  },
  line: {
    label: "Línea",
    Icon: TrendingUp,
    color: "text-green-600 dark:text-green-400",
  },
  pie: {
    label: "Circular",
    Icon: PieChart,
    color: "text-purple-600 dark:text-purple-400",
  },
  table: {
    label: "Tabla",
    Icon: Table2,
    color: "text-primary-600 dark:text-primary-400",
  },
  number: {
    label: "Número",
    Icon: Hash,
    color: "text-orange-600 dark:text-orange-400",
  },
};

// ─── Sub-components ───────────────────────────────────────────────────────────

/**
 * Renders a big-number display for single metric responses.
 */
function NumberDisplay({ data }: { data: Record<string, unknown>[] }) {
  if (data.length === 0) return null;

  const firstRow = data[0];
  const entries = Object.entries(firstRow);

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="flex flex-col items-center justify-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/40 px-4 py-5 text-center"
        >
          <span className="text-3xl font-bold tabular-nums text-foreground">
            {typeof value === "number"
              ? value.toLocaleString("es-CO")
              : String(value ?? "—")}
          </span>
          <span className="mt-1.5 text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
            {key.replace(/_/g, " ")}
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * Renders a data table from the response data array.
 * Used as the primary renderer for chart_type "table" and as a fallback
 * for visual chart types (bar, line, pie) until a chart library is integrated.
 */
function DataTable({ data }: { data: Record<string, unknown>[] }) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
        Sin datos para mostrar.
      </p>
    );
  }

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto rounded-md border border-[hsl(var(--border))]">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col} className="whitespace-nowrap text-xs font-semibold">
                {col.replace(/_/g, " ")}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {columns.map((col) => {
                const cellValue = row[col];
                const formatted =
                  typeof cellValue === "number"
                    ? cellValue.toLocaleString("es-CO")
                    : cellValue === null || cellValue === undefined
                      ? "—"
                      : String(cellValue);
                return (
                  <TableCell key={col} className="text-sm tabular-nums">
                    {formatted}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/**
 * Placeholder card for chart types whose rendering is deferred.
 * Shows a visual placeholder with the chart type label.
 */
function ChartPlaceholder({
  chartType,
  data,
}: {
  chartType: AIQueryResponse["chart_type"];
  data: Record<string, unknown>[];
}) {
  const config = CHART_TYPE_CONFIG[chartType];
  const Icon = config.Icon;

  return (
    <div className="space-y-3">
      {/* Visual placeholder */}
      <div
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed",
          "border-[hsl(var(--border))] bg-[hsl(var(--muted))]/30 py-6",
        )}
      >
        <Icon className={cn("h-8 w-8", config.color)} />
        <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
          Gráfico de {config.label.toLowerCase()}
        </p>
        <p className="text-xs text-[hsl(var(--muted-foreground))]/70">
          Visualización gráfica próximamente — datos disponibles abajo
        </p>
      </div>
      {/* Table fallback */}
      <DataTable data={data} />
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded-full" />
          <Skeleton className="h-4 w-32" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-4 w-3/5" />
        <div className="mt-4 space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center gap-4 py-10 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 dark:bg-primary-900/20">
          <Lightbulb className="h-6 w-6 text-primary-600 dark:text-primary-400" />
        </div>
        <div className="space-y-1.5 max-w-sm">
          <p className="text-sm font-medium text-foreground">
            Pregunta a la IA sobre tus datos
          </p>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Prueba preguntas como:
          </p>
          <ul className="mt-2 space-y-1 text-xs text-[hsl(var(--muted-foreground))]">
            <li className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-primary-500 shrink-0" />
              "¿Cuántos pacientes vinieron este mes?"
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-primary-500 shrink-0" />
              "¿Cuál es la tasa de inasistencia?"
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-primary-500 shrink-0" />
              "¿Cuánto ingresé esta semana?"
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-primary-500 shrink-0" />
              "¿Cuál es el procedimiento más realizado?"
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

/**
 * AIResponseDisplay — Renders the AI analytics response.
 *
 * Handles four states:
 * - isLoading: skeleton pulse animation
 * - response is null: empty state with helpful example questions
 * - chart_type "number": big metric tiles
 * - chart_type "table": full data table
 * - chart_type "bar" | "line" | "pie": visual placeholder + table fallback
 */
export function AIResponseDisplay({
  response,
  isLoading,
  className,
}: AIResponseDisplayProps) {
  if (isLoading) {
    return (
      <div className={className}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (!response) {
    return (
      <div className={className}>
        <EmptyState />
      </div>
    );
  }

  const chartConfig = CHART_TYPE_CONFIG[response.chart_type];
  const ChartIcon = chartConfig.Icon;

  return (
    <div className={className}>
      <Card className="border-primary-200 dark:border-primary-800">
        {/* ─── Header ────────────────────────────────────────────────────── */}
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-primary-600 shrink-0" />
              Respuesta de la IA
            </CardTitle>
            <div className="flex items-center gap-2">
              {/* Query key badge */}
              <Badge variant="outline" className="text-xs font-mono gap-1">
                {response.query_key}
              </Badge>
              {/* Chart type badge */}
              <Badge variant="outline" className="text-xs gap-1">
                <ChartIcon className={cn("h-3 w-3", chartConfig.color)} />
                {chartConfig.label}
              </Badge>
            </div>
          </div>
          {/* Answer text */}
          <CardDescription className="mt-2 text-sm text-foreground leading-relaxed bg-primary-50/60 dark:bg-primary-900/20 rounded-md px-3 py-2 border border-primary-100 dark:border-primary-800">
            {response.answer}
          </CardDescription>
        </CardHeader>

        {/* ─── Data visualization ───────────────────────────────────────── */}
        {response.data.length > 0 && (
          <CardContent className="pt-0">
            {response.chart_type === "number" && (
              <NumberDisplay data={response.data} />
            )}
            {response.chart_type === "table" && (
              <DataTable data={response.data} />
            )}
            {(response.chart_type === "bar" ||
              response.chart_type === "line" ||
              response.chart_type === "pie") && (
              <ChartPlaceholder
                chartType={response.chart_type}
                data={response.data}
              />
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
