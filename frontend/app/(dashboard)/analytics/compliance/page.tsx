"use client";

/**
 * Workflow compliance analytics page.
 *
 * Displays 7 compliance checks from GET /analytics/workflow-compliance.
 * Each check is color-coded by severity and shows violation count.
 * Expandable sections reveal individual violations.
 * Optional AI narrative toggle generates a Spanish summary via Claude.
 *
 * Gated to Pro+ plans — shows upgrade prompt for Free/Starter.
 */

import { useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Lock,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useWorkflowCompliance,
  type ComplianceCheck,
} from "@/lib/hooks/use-analytics";
import { useAuth } from "@/lib/hooks/use-auth";

// ─── Check Name Translations ─────────────────────────────────────────────────

const CHECK_LABELS: Record<string, string> = {
  appointment_no_record: "Citas sin registro clinico",
  record_no_diagnosis: "Registros sin diagnostico",
  record_no_procedure: "Registros sin procedimiento",
  plan_consent_unsigned: "Planes sin consentimiento firmado",
  plan_item_overdue: "Items de plan vencidos (+90 dias)",
  lab_order_overdue: "Ordenes de laboratorio vencidas",
  patient_no_anamnesis: "Pacientes sin anamnesis",
};

// ─── Severity Helpers ────────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  high: "border-red-300 bg-red-50 dark:border-red-700/40 dark:bg-red-900/10",
  medium: "border-amber-300 bg-amber-50 dark:border-amber-700/40 dark:bg-amber-900/10",
  low: "border-blue-300 bg-blue-50 dark:border-blue-700/40 dark:bg-blue-900/10",
};

const SEVERITY_BADGE: Record<string, React.ComponentProps<typeof Badge>["variant"]> = {
  high: "destructive",
  warning: "warning",
  low: "outline",
};

const SEVERITY_LABELS: Record<string, string> = {
  high: "Alta",
  medium: "Media",
  low: "Baja",
};

// ─── Compliance Check Card ───────────────────────────────────────────────────

function ComplianceCheckCard({ check }: { check: ComplianceCheck }) {
  const [expanded, setExpanded] = useState(false);
  const label = CHECK_LABELS[check.check_key] ?? check.check_name;

  return (
    <Card className={SEVERITY_COLORS[check.severity] ?? SEVERITY_COLORS.low}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm font-semibold">{label}</CardTitle>
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant={SEVERITY_BADGE[check.severity] ?? "outline"}>
              {SEVERITY_LABELS[check.severity] ?? check.severity}
            </Badge>
            <span className="text-lg font-bold tabular-nums">
              {check.violation_count}
            </span>
          </div>
        </div>
      </CardHeader>

      {check.violations.length > 0 && (
        <CardContent className="pt-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="text-xs px-0 hover:bg-transparent"
          >
            {expanded ? (
              <ChevronDown className="h-3.5 w-3.5 mr-1" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 mr-1" />
            )}
            {expanded ? "Ocultar detalles" : "Ver detalles"}
          </Button>

          {expanded && (
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-xs" aria-label={`Violaciones: ${label}`}>
                <thead>
                  <tr className="border-b border-[hsl(var(--border))]">
                    <th className="px-2 py-1.5 text-left font-medium text-muted-foreground">
                      Paciente
                    </th>
                    <th className="px-2 py-1.5 text-left font-medium text-muted-foreground">
                      Tipo
                    </th>
                    <th className="px-2 py-1.5 text-right font-medium text-muted-foreground">
                      Dias vencido
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))]">
                  {check.violations.slice(0, 20).map((v, i) => (
                    <tr key={i}>
                      <td className="px-2 py-1.5 font-mono text-muted-foreground">
                        {v.patient_id.slice(0, 8)}...
                      </td>
                      <td className="px-2 py-1.5">
                        {v.reference_type}
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">
                        {v.days_overdue}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {check.violations.length > 20 && (
                <p className="text-xs text-muted-foreground mt-2 px-2">
                  Mostrando 20 de {check.violations.length} violaciones.
                </p>
              )}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const [lookbackDays, setLookbackDays] = useState(30);
  const [enableAi, setEnableAi] = useState(false);

  const { tenant } = useAuth();
  const planName = tenant?.plan_name?.toLowerCase() ?? "free";
  const isPlanGated = planName === "free" || planName === "starter";

  const { data, isLoading, isError, refetch } = useWorkflowCompliance(
    lookbackDays,
    enableAi,
  );

  if (isPlanGated) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Lock className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
          <p className="text-sm font-medium text-foreground">
            Funcion disponible en plan Pro o superior
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Actualiza tu plan para acceder al monitor de cumplimiento de workflow clinico.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Controls ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-center gap-2">
          <Label htmlFor="lookback" className="text-sm whitespace-nowrap">
            Periodo:
          </Label>
          <Select
            value={String(lookbackDays)}
            onValueChange={(v) => setLookbackDays(Number(v))}
          >
            <SelectTrigger id="lookback" className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Ultimos 7 dias</SelectItem>
              <SelectItem value="30">Ultimos 30 dias</SelectItem>
              <SelectItem value="90">Ultimos 90 dias</SelectItem>
              <SelectItem value="365">Ultimo ano</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          variant={enableAi ? "default" : "outline"}
          size="sm"
          onClick={() => setEnableAi(!enableAi)}
          className="flex items-center gap-1.5"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {enableAi ? "IA activada" : "Activar IA"}
        </Button>
      </div>

      {/* ── Loading ── */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-20 rounded-lg" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))}
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {isError && (
        <Card className="border-destructive/30">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-destructive" />
              <p className="text-sm text-destructive">
                No se pudo cargar los datos de cumplimiento.
              </p>
            </div>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Data ── */}
      {data && (
        <>
          {/* Total KPI */}
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Total de violaciones
                  </p>
                  <p className="text-3xl font-bold text-foreground tabular-nums">
                    {data.total_violations}
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">
                  {data.checks.length} verificaciones | Ultimos {data.lookback_days} dias
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Check cards grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.checks.map((check) => (
              <ComplianceCheckCard key={check.check_key} check={check} />
            ))}
          </div>

          {/* AI Narrative */}
          {enableAi && data.ai_narrative && (
            <Card className="border-purple-200 dark:border-purple-700/40">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-purple-500" />
                  Resumen de IA
                </CardTitle>
                <CardDescription>
                  Analisis generado automaticamente por inteligencia artificial.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                  {data.ai_narrative}
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
