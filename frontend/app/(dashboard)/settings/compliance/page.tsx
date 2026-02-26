"use client";

import * as React from "react";
import { useCountryConfig } from "@/lib/hooks/use-compliance";
import { Badge } from "@/components/ui/badge";
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
import { ShieldCheck, FileText, Building2 } from "lucide-react";

export default function ComplianceSettingsPage() {
  const { data: config, isLoading } = useCountryConfig();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <h1 className="text-2xl font-bold tracking-tight">Configuración de cumplimiento</h1>
        <p className="text-[hsl(var(--muted-foreground))]">Cargando...</p>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <h1 className="text-2xl font-bold tracking-tight">Configuración de cumplimiento</h1>
        <p className="text-[hsl(var(--muted-foreground))]">
          No se pudo cargar la configuración.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Configuración de cumplimiento</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Configuración normativa para {config.country_name}
        </p>
      </div>

      {/* Country info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary-600" />
            <CardTitle>País: {config.country_name}</CardTitle>
          </div>
          <CardDescription>
            Sistema de códigos: {config.procedure_code_system}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {Object.entries(config.feature_flags).map(([key, value]) => (
              <Badge
                key={key}
                variant={value ? "default" : "outline"}
                className={value ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300" : ""}
              >
                {key}: {String(value)}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Regulatory references */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary-600" />
            <CardTitle>Referencias normativas</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Título</TableHead>
                <TableHead>Tema</TableHead>
                <TableHead>Fecha límite</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {config.regulatory_references.map((ref) => (
                <TableRow key={ref.code}>
                  <TableCell className="font-mono text-sm">{ref.code}</TableCell>
                  <TableCell className="font-medium">{ref.title}</TableCell>
                  <TableCell>{ref.topic}</TableCell>
                  <TableCell>
                    {ref.deadline ? (
                      <Badge variant="outline">{ref.deadline}</Badge>
                    ) : (
                      <span className="text-[hsl(var(--muted-foreground))]">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Retention rules */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary-600" />
            <CardTitle>Reglas de retención</CardTitle>
          </div>
          <CardDescription>
            Periodos mínimos de conservación según normatividad vigente
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tipo de documento</TableHead>
                <TableHead>Años</TableHead>
                <TableHead>Regulación</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(config.retention_rules).map(([key, rule]) => {
                const r = rule as { years: number; regulation: string };
                return (
                  <TableRow key={key}>
                    <TableCell className="font-medium capitalize">
                      {key.replace(/_/g, " ")}
                    </TableCell>
                    <TableCell className="tabular-nums">{r.years} años</TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                      {r.regulation}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
