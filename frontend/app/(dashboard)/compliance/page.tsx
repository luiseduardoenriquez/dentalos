"use client";

import * as React from "react";
import { useRDAStatus } from "@/lib/hooks/use-compliance";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { RefreshCw, AlertTriangle, CheckCircle2, Clock } from "lucide-react";

function getLevelBadge(level: string) {
  switch (level) {
    case "compliant":
      return <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">Cumple</Badge>;
    case "improving":
      return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">En mejora</Badge>;
    case "at_risk":
      return <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">En riesgo</Badge>;
    case "critical":
      return <Badge className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">Crítico</Badge>;
    default:
      return <Badge variant="outline">{level}</Badge>;
  }
}

function getSeverityBadge(severity: string) {
  switch (severity) {
    case "critical":
      return <Badge variant="destructive">Crítico</Badge>;
    case "required":
      return <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">Requerido</Badge>;
    case "recommended":
      return <Badge variant="outline">Recomendado</Badge>;
    default:
      return <Badge variant="outline">{severity}</Badge>;
  }
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr);
  const now = new Date();
  return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

export default function RDADashboardPage() {
  const { data: status, isLoading, refetch, isFetching } = useRDAStatus();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
      </div>
    );
  }

  if (!status) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-[hsl(var(--muted-foreground))]">
          No se pudo cargar el estado de cumplimiento RDA.
        </CardContent>
      </Card>
    );
  }

  const daysLeft = daysUntil(status.deadline);

  return (
    <div className="flex flex-col gap-6">
      {/* Summary row */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Overall score */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Cumplimiento general</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold tabular-nums">
                {status.overall_compliance_percentage.toFixed(1)}%
              </span>
              {getLevelBadge(status.compliance_level)}
            </div>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              {status.total_records_analyzed} registros analizados
              {status.cached && " (en caché)"}
            </p>
          </CardContent>
        </Card>

        {/* Deadline */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Fecha límite Res. 1888</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <Clock className="h-5 w-5 text-[hsl(var(--muted-foreground))]" />
              <span className="text-2xl font-bold tabular-nums">
                {daysLeft > 0 ? `${daysLeft} días` : "Vencido"}
              </span>
            </div>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              1 de abril de 2026
            </p>
          </CardContent>
        </Card>

        {/* Gaps count */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Brechas detectadas</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              <span className="text-2xl font-bold tabular-nums">
                {status.gaps.length}
              </span>
            </div>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              {status.gaps.filter((g) => g.severity === "critical").length} críticas
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Refresh button */}
      <div className="flex justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          Actualizar
        </Button>
      </div>

      {/* Module breakdowns */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {status.modules.map((mod) => (
          <Card key={mod.module}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">{mod.label}</CardTitle>
              <CardDescription>
                {mod.compliant_fields}/{mod.total_fields} campos
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 rounded-full bg-[hsl(var(--muted))]">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      mod.compliance_percentage >= 95
                        ? "bg-green-500"
                        : mod.compliance_percentage >= 80
                          ? "bg-blue-500"
                          : mod.compliance_percentage >= 50
                            ? "bg-yellow-500"
                            : "bg-red-500"
                    }`}
                    style={{ width: `${Math.min(mod.compliance_percentage, 100)}%` }}
                  />
                </div>
                <span className="text-sm font-medium tabular-nums w-12 text-right">
                  {mod.compliance_percentage.toFixed(0)}%
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Gaps table */}
      {status.gaps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Brechas de cumplimiento</CardTitle>
            <CardDescription>
              Ordenadas por impacto (severidad x porcentaje de brecha)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Campo</TableHead>
                  <TableHead>Módulo</TableHead>
                  <TableHead>Severidad</TableHead>
                  <TableHead className="text-right">Brecha</TableHead>
                  <TableHead>Acción correctiva</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {status.gaps.map((gap, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-medium">{gap.field_name}</TableCell>
                    <TableCell>{gap.module}</TableCell>
                    <TableCell>{getSeverityBadge(gap.severity)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {gap.gap_percentage.toFixed(1)}%
                    </TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                      {gap.corrective_action}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
