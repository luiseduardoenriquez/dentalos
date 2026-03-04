"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, AlertCircle } from "lucide-react";
import { apiGet } from "@/lib/api-client";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SurveyResponse {
  id: string;
  patient_name: string;
  nps_score: number;
  csat_score: number | null;
  comments: string | null;
  doctor_name: string | null;
  responded_at: string;
}

interface SurveyListResponse {
  items: SurveyResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ─── NPS score badge ──────────────────────────────────────────────────────────

function NpsScoreBadge({ score }: { score: number }) {
  const isPromoter = score >= 9;
  const isPassive = score >= 7 && score <= 8;

  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-bold tabular-nums w-7 justify-center",
        !isPromoter && !isPassive && score <= 3
          ? "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700"
          : "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-700",
      )}
    >
      {score}
    </Badge>
  );
}

// ─── Survey detail dialog ─────────────────────────────────────────────────────

function SurveyDetailDialog({
  survey,
  onClose,
}: {
  survey: SurveyResponse | null;
  onClose: () => void;
}) {
  if (!survey) return null;

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Respuesta de encuesta</DialogTitle>
          <DialogDescription>
            Paciente: {survey.patient_name} · {formatDate(survey.responded_at)}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {/* NPS */}
          <div className="flex items-center justify-between rounded-lg border border-[hsl(var(--border))] p-3">
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Puntuación NPS</p>
              <p className="text-2xl font-bold tabular-nums text-foreground">
                {survey.nps_score}
                <span className="text-sm font-normal text-[hsl(var(--muted-foreground))]">
                  /10
                </span>
              </p>
            </div>
            <NpsScoreBadge score={survey.nps_score} />
          </div>

          {/* CSAT */}
          {survey.csat_score != null && (
            <div className="flex items-center justify-between rounded-lg border border-[hsl(var(--border))] p-3">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Satisfacción (CSAT)</p>
                <p className="text-2xl font-bold tabular-nums text-foreground">
                  {survey.csat_score}
                  <span className="text-sm font-normal text-[hsl(var(--muted-foreground))]">
                    /5
                  </span>
                </p>
              </div>
            </div>
          )}

          {/* Doctor */}
          {survey.doctor_name && (
            <div className="space-y-0.5">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Doctor atendiendo</p>
              <p className="text-sm font-medium text-foreground">{survey.doctor_name}</p>
            </div>
          )}

          {/* Comments */}
          <div className="space-y-1">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Comentarios</p>
            {survey.comments ? (
              <p className="text-sm text-foreground rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] p-3">
                {survey.comments}
              </p>
            ) : (
              <p className="text-sm italic text-[hsl(var(--muted-foreground))]">
                Sin comentarios.
              </p>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface DetractorInboxProps {
  className?: string;
}

export function DetractorInbox({ className }: DetractorInboxProps) {
  const [selectedSurvey, setSelectedSurvey] = React.useState<SurveyResponse | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["surveys-detractors"],
    queryFn: () =>
      apiGet<SurveyListResponse>("/surveys?responded=true&page=1&page_size=20"),
    staleTime: 2 * 60_000,
    select: (res) => ({
      ...res,
      items: res.items.filter((s) => s.nps_score <= 6),
    }),
  });

  const detractors = data?.items ?? [];

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Alertas de Detractores
              </CardTitle>
              <CardDescription className="mt-1">
                Respuestas con NPS 0–6 que requieren atención.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isLoading && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full rounded" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <AlertCircle className="h-6 w-6 text-red-500" />
              <p className="text-sm text-red-600 dark:text-red-400">
                Error al cargar los detractores.
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Reintentar
              </Button>
            </div>
          ) : detractors.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 gap-2 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <AlertTriangle className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <p className="text-sm font-medium text-foreground">
                Sin detractores recientes
              </p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                No hay respuestas con NPS 0–6 en las últimas encuestas.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[hsl(var(--border))]">
              {detractors.map((survey) => (
                <button
                  key={survey.id}
                  type="button"
                  onClick={() => setSelectedSurvey(survey)}
                  className="w-full flex items-start gap-3 py-3 text-left hover:bg-[hsl(var(--muted))]/40 transition-colors rounded-lg px-2 -mx-2"
                >
                  <NpsScoreBadge score={survey.nps_score} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {survey.patient_name}
                    </p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] truncate mt-0.5">
                      {survey.comments ? (
                        <span className="italic">&ldquo;{survey.comments}&rdquo;</span>
                      ) : (
                        <span className="italic">Sin comentarios</span>
                      )}
                    </p>
                    {survey.doctor_name && (
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                        Dr. {survey.doctor_name}
                      </p>
                    )}
                  </div>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] whitespace-nowrap shrink-0">
                    {formatDate(survey.responded_at)}
                  </p>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <SurveyDetailDialog
        survey={selectedSurvey}
        onClose={() => setSelectedSurvey(null)}
      />
    </>
  );
}
