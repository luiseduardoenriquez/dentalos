"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Brain, AlertCircle, Users, CalendarX2 } from "lucide-react";
import { formatTime, cn } from "@/lib/utils";
import { NoShowRiskBadge } from "@/components/no-show-risk-badge";

// ─── Types (match backend IntelligenceResponse) ──────────────────────────────

type RiskLevel = "low" | "medium" | "high";

interface NoShowRisk {
  appointment_id: string;
  patient_name: string;
  risk_level: RiskLevel;
  risk_score: number;
  factors: Record<string, unknown>;
}

interface GapAnalysis {
  slot_start: string;
  slot_end: string;
  doctor_id: string;
  doctor_name: string;
  suggested_patients: { patient_id: string; name: string; reason: string }[];
}

interface UtilizationMetric {
  doctor_id: string;
  doctor_name: string;
  date: string;
  completed_minutes: number;
  available_minutes: number;
  utilization_pct: number;
}

interface ScheduleIntelligenceData {
  date: string;
  no_show_risks: NoShowRisk[];
  gaps: GapAnalysis[];
  utilization: UtilizationMetric[];
  overbooking_suggestions: unknown[];
}

// ─── Utilization Bar ─────────────────────────────────────────────────────────

function UtilizationBar({
  percentage,
  doctorName,
}: {
  percentage: number;
  doctorName: string;
}) {
  const barColor =
    percentage >= 80
      ? "bg-green-500"
      : percentage >= 50
        ? "bg-primary-500"
        : "bg-yellow-400";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-foreground truncate max-w-[120px]">
          {doctorName}
        </span>
        <span className="tabular-nums text-[hsl(var(--muted-foreground))] shrink-0 ml-2">
          {percentage.toFixed(0)}%
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-100 dark:bg-zinc-800">
        <div
          className={cn("h-1.5 rounded-full transition-all", barColor)}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ScheduleIntelligencePanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["schedule-intelligence"],
    queryFn: () => apiGet<ScheduleIntelligenceData>("/analytics/schedule-intelligence"),
    staleTime: 3 * 60_000,
    refetchInterval: 5 * 60_000,
  });

  return (
    <div className="flex flex-col gap-4 w-full">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Brain className="h-4 w-4 text-primary-600" />
        <h2 className="text-sm font-semibold text-foreground">
          Inteligencia de agenda
        </h2>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-20 rounded-lg" />
        </div>
      ) : isError || !data ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-800 px-3 py-2">
          <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />
          <p className="text-xs text-red-600 dark:text-red-400">
            No se pudo cargar la inteligencia.
          </p>
        </div>
      ) : (
        <>
          {/* ─── No-show Risks ─────────────────────────────────────────── */}
          <Card>
            <CardHeader className="pb-2 pt-3 px-3">
              <CardTitle className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide flex items-center gap-1.5">
                <CalendarX2 className="h-3.5 w-3.5" />
                Riesgo de inasistencia
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3">
              {data.no_show_risks.length === 0 ? (
                <p className="text-xs text-[hsl(var(--muted-foreground))] py-1">
                  No hay citas en riesgo hoy.
                </p>
              ) : (
                <ul className="space-y-2">
                  {data.no_show_risks.slice(0, 5).map((risk) => (
                    <li
                      key={risk.appointment_id}
                      className="flex items-center justify-between gap-2"
                    >
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-foreground truncate">
                          {risk.patient_name}
                        </p>
                      </div>
                      <NoShowRiskBadge
                        riskLevel={risk.risk_level}
                        riskScore={risk.risk_score}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* ─── Gaps / Suggestions ────────────────────────────────────── */}
          <Card>
            <CardHeader className="pb-2 pt-3 px-3">
              <CardTitle className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5" />
                Espacios libres sugeridos
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3">
              {data.gaps.length === 0 ? (
                <p className="text-xs text-[hsl(var(--muted-foreground))] py-1">
                  La agenda está bien optimizada.
                </p>
              ) : (
                <ul className="space-y-2">
                  {data.gaps.slice(0, 4).map((gap, i) => (
                    <li
                      key={i}
                      className="rounded-md border border-[hsl(var(--border))] p-2 text-xs space-y-0.5"
                    >
                      <p className="font-medium text-foreground">
                        {formatTime(gap.slot_start)} – {formatTime(gap.slot_end)}
                      </p>
                      <p className="text-[hsl(var(--muted-foreground))]">
                        {gap.doctor_name}
                      </p>
                      {gap.suggested_patients.length > 0 && (
                        <p className="text-primary-600 dark:text-primary-400">
                          Sugerido: {gap.suggested_patients[0].name}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* ─── Utilization ───────────────────────────────────────────── */}
          <Card>
            <CardHeader className="pb-2 pt-3 px-3">
              <CardTitle className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                Ocupación por doctor
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 space-y-3">
              {data.utilization.length === 0 ? (
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Sin datos de ocupación.
                </p>
              ) : (
                data.utilization.map((u) => (
                  <UtilizationBar
                    key={u.doctor_id}
                    doctorName={u.doctor_name}
                    percentage={u.utilization_pct}
                  />
                ))
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
