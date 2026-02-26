"use client";

import * as React from "react";
import {
  useRIPSBatches,
  useGenerateRIPS,
  useValidateRIPS,
} from "@/lib/hooks/use-compliance";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Download, FileText, Play, ShieldCheck } from "lucide-react";

function getStatusBadge(status: string) {
  switch (status) {
    case "queued":
      return <Badge variant="outline">En cola</Badge>;
    case "generating":
      return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">Generando</Badge>;
    case "generated":
      return <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">Generado</Badge>;
    case "validated":
      return <Badge className="bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300">Validado</Badge>;
    case "failed":
      return <Badge variant="destructive">Fallido</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export default function RIPSPage() {
  const [page, setPage] = React.useState(1);
  const [periodStart, setPeriodStart] = React.useState("");
  const [periodEnd, setPeriodEnd] = React.useState("");
  const { data, isLoading } = useRIPSBatches(page);
  const generateMutation = useGenerateRIPS();
  const validateMutation = useValidateRIPS();

  const handleGenerate = () => {
    if (!periodStart || !periodEnd) return;
    generateMutation.mutate({
      period_start: periodStart,
      period_end: periodEnd,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Generate section */}
      <Card>
        <CardHeader>
          <CardTitle>Generar RIPS</CardTitle>
          <CardDescription>
            Seleccione el periodo para generar los archivos RIPS (Resolución 3374)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="period-start">Inicio del periodo</Label>
              <Input
                id="period-start"
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="period-end">Fin del periodo</Label>
              <Input
                id="period-end"
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
              />
            </div>
            <Button
              onClick={handleGenerate}
              disabled={!periodStart || !periodEnd || generateMutation.isPending}
            >
              <Play className="mr-2 h-4 w-4" />
              Generar
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Batch history */}
      <Card>
        <CardHeader>
          <CardTitle>Historial de lotes</CardTitle>
          <CardDescription>
            {data ? `${data.total} lotes generados` : "Cargando..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">Cargando...</p>
          ) : !data?.items.length ? (
            <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">
              No hay lotes RIPS generados.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Periodo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Archivos</TableHead>
                  <TableHead className="text-right">Errores</TableHead>
                  <TableHead className="text-right">Avisos</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((batch) => (
                  <TableRow key={batch.id}>
                    <TableCell className="font-medium">
                      {batch.period_start} — {batch.period_end}
                    </TableCell>
                    <TableCell>{getStatusBadge(batch.status)}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {batch.file_types.map((ft) => (
                          <Badge key={ft} variant="outline" className="text-xs">
                            {ft}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {batch.error_count}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {batch.warning_count}
                    </TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                      {new Date(batch.created_at).toLocaleDateString("es-CO")}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {batch.status === "generated" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => validateMutation.mutate(batch.id)}
                            disabled={validateMutation.isPending}
                            title="Validar"
                          >
                            <ShieldCheck className="h-4 w-4" />
                          </Button>
                        )}
                        {batch.files.length > 0 && (
                          <Button variant="ghost" size="sm" title="Descargar">
                            <Download className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {data && data.total > 20 && (
            <div className="flex justify-center gap-2 mt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                Anterior
              </Button>
              <span className="flex items-center text-sm text-[hsl(var(--muted-foreground))]">
                Página {data.page} de {Math.ceil(data.total / data.page_size)}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(data.total / data.page_size)}
              >
                Siguiente
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
