"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Star, Send, ThumbsUp, BarChart2, MessageSquare, TrendingUp, AlertCircle } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReputationDashboard {
  nps_score: number;
  average_rating: number;
  total_surveys: number;
  response_rate: number;
  promoters_count: number;
  passives_count: number;
  detractors_count: number;
}

interface FeedbackItem {
  id: string;
  created_at: string;
  patient_name: string;
  score: number;
  feedback_text: string | null;
  routed_to: "google_review" | "private";
}

interface FeedbackListResponse {
  items: FeedbackItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Star Rating Display ──────────────────────────────────────────────────────

function StarRating({ score, max = 5 }: { score: number; max?: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: max }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            "h-3.5 w-3.5",
            i < score
              ? "fill-yellow-400 text-yellow-400"
              : "fill-transparent text-slate-300 dark:text-zinc-600",
          )}
        />
      ))}
    </div>
  );
}

// ─── NPS Category ─────────────────────────────────────────────────────────────

function npsColor(score: number): string {
  if (score >= 50) return "text-green-600 dark:text-green-400";
  if (score >= 0) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-64 rounded bg-slate-200 dark:bg-zinc-700" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-xl bg-slate-100 dark:bg-zinc-800" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-slate-100 dark:bg-zinc-800" />
      <div className="h-64 rounded-xl bg-slate-100 dark:bg-zinc-800" />
    </div>
  );
}

// ─── Send Survey Modal ────────────────────────────────────────────────────────

function SendSurveyModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [patientId, setPatientId] = React.useState("");

  const { mutate: sendSurvey, isPending } = useMutation({
    mutationFn: (payload: { patient_id: string }) =>
      apiPost<void>("/reputation/surveys/send", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reputation-feedback"] });
      setPatientId("");
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!patientId.trim()) return;
    sendSurvey({ patient_id: patientId.trim() });
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Enviar encuesta de satisfacción</DialogTitle>
          <DialogDescription>
            Se enviará una encuesta NPS al paciente por WhatsApp, SMS o correo
            según su configuración.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label
              htmlFor="patient-id-input"
              className="text-sm font-medium text-foreground"
            >
              ID del paciente
            </label>
            <Input
              id="patient-id-input"
              placeholder="UUID del paciente..."
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              required
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending || !patientId.trim()}>
              {isPending ? "Enviando..." : "Enviar encuesta"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReputationDashboardPage() {
  const [sendModalOpen, setSendModalOpen] = React.useState(false);

  const {
    data: dashboard,
    isLoading: isLoadingDashboard,
    isError: isDashboardError,
  } = useQuery({
    queryKey: ["reputation-dashboard"],
    queryFn: () => apiGet<ReputationDashboard>("/reputation/dashboard"),
    staleTime: 2 * 60_000,
  });

  const {
    data: feedbackData,
    isLoading: isLoadingFeedback,
  } = useQuery({
    queryKey: ["reputation-feedback"],
    queryFn: () => apiGet<FeedbackListResponse>("/reputation/feedback"),
    staleTime: 60_000,
  });

  const isLoading = isLoadingDashboard || isLoadingFeedback;

  if (isLoading) return <PageSkeleton />;

  if (isDashboardError || !dashboard) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          No se pudo cargar el panel de reputación.
        </p>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Intenta de nuevo más tarde.
        </p>
      </div>
    );
  }

  const feedbackItems = feedbackData?.items ?? [];

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Reputación
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Monitorea la satisfacción de tus pacientes y gestiona reseñas en Google.
          </p>
        </div>
        <Button onClick={() => setSendModalOpen(true)}>
          <Send className="mr-2 h-4 w-4" />
          Enviar encuesta
        </Button>
      </div>

      {/* ─── Stats Cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {/* NPS Score */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" />
              NPS Score
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p
              className={cn(
                "text-4xl font-bold tabular-nums",
                npsColor(dashboard.nps_score),
              )}
            >
              {(dashboard.nps_score ?? 0) > 0 ? "+" : ""}
              {dashboard.nps_score ?? 0}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              {dashboard.promoters_count ?? 0} promotores · {dashboard.detractors_count ?? 0} detractores
            </p>
          </CardContent>
        </Card>

        {/* Average Rating */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Star className="h-3.5 w-3.5" />
              Calificación promedio
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold tabular-nums text-foreground">
              {(dashboard.average_rating ?? 0).toFixed(1)}
            </p>
            <div className="mt-1">
              <StarRating score={Math.round(dashboard.average_rating ?? 0)} />
            </div>
          </CardContent>
        </Card>

        {/* Total Surveys */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5" />
              Encuestas enviadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold tabular-nums text-foreground">
              {(dashboard.total_surveys ?? 0).toLocaleString("es-CO")}
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              Total acumulado
            </p>
          </CardContent>
        </Card>

        {/* Response Rate */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <BarChart2 className="h-3.5 w-3.5" />
              Tasa de respuesta
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold tabular-nums text-foreground">
              {(dashboard.response_rate ?? 0).toFixed(0)}%
            </p>
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
              De encuestas enviadas
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ─── NPS Distribution ────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Distribución NPS</CardTitle>
          <CardDescription>
            Promotores (9-10) · Pasivos (7-8) · Detractores (0-6)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* Promotores */}
            <div className="flex items-center gap-3">
              <span className="w-24 text-sm text-green-600 dark:text-green-400 font-medium shrink-0">
                Promotores
              </span>
              <div className="flex-1 h-3 rounded-full bg-slate-100 dark:bg-zinc-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-green-500 transition-all"
                  style={{
                    width:
                      (dashboard.total_surveys ?? 0) > 0
                        ? `${((dashboard.promoters_count ?? 0) / (dashboard.total_surveys ?? 1)) * 100}%`
                        : "0%",
                  }}
                />
              </div>
              <span className="w-8 text-right text-sm font-medium tabular-nums text-foreground shrink-0">
                {dashboard.promoters_count ?? 0}
              </span>
            </div>
            {/* Pasivos */}
            <div className="flex items-center gap-3">
              <span className="w-24 text-sm text-yellow-600 dark:text-yellow-400 font-medium shrink-0">
                Pasivos
              </span>
              <div className="flex-1 h-3 rounded-full bg-slate-100 dark:bg-zinc-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-yellow-400 transition-all"
                  style={{
                    width:
                      (dashboard.total_surveys ?? 0) > 0
                        ? `${((dashboard.passives_count ?? 0) / (dashboard.total_surveys ?? 1)) * 100}%`
                        : "0%",
                  }}
                />
              </div>
              <span className="w-8 text-right text-sm font-medium tabular-nums text-foreground shrink-0">
                {dashboard.passives_count ?? 0}
              </span>
            </div>
            {/* Detractores */}
            <div className="flex items-center gap-3">
              <span className="w-24 text-sm text-red-600 dark:text-red-400 font-medium shrink-0">
                Detractores
              </span>
              <div className="flex-1 h-3 rounded-full bg-slate-100 dark:bg-zinc-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-red-500 transition-all"
                  style={{
                    width:
                      (dashboard.total_surveys ?? 0) > 0
                        ? `${((dashboard.detractors_count ?? 0) / (dashboard.total_surveys ?? 1)) * 100}%`
                        : "0%",
                  }}
                />
              </div>
              <span className="w-8 text-right text-sm font-medium tabular-nums text-foreground shrink-0">
                {dashboard.detractors_count ?? 0}
              </span>
            </div>
          </div>

          {/* Chart placeholder */}
          <div className="mt-6 h-40 rounded-lg border border-dashed border-[hsl(var(--border))] flex items-center justify-center bg-[hsl(var(--muted))]/30">
            <div className="text-center">
              <BarChart2 className="mx-auto h-8 w-8 text-[hsl(var(--muted-foreground))]" />
              <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
                Gráfica de tendencia próximamente
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ─── Feedback Queue ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ThumbsUp className="h-4 w-4 text-primary-600" />
            Cola de feedback
          </CardTitle>
          <CardDescription>
            Respuestas recientes de pacientes y su enrutamiento.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {feedbackItems.length === 0 ? (
            <p className="py-8 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No hay respuestas de encuestas todavía.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Paciente</TableHead>
                  <TableHead>Calificación</TableHead>
                  <TableHead>Comentario</TableHead>
                  <TableHead>Enrutado a</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {feedbackItems.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                      {formatDate(item.created_at)}
                    </TableCell>
                    <TableCell className="text-sm font-medium text-foreground">
                      {item.patient_name}
                    </TableCell>
                    <TableCell>
                      <StarRating score={item.score} />
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <p className="text-sm text-[hsl(var(--muted-foreground))] truncate">
                        {item.feedback_text ?? (
                          <span className="italic">Sin comentario</span>
                        )}
                      </p>
                    </TableCell>
                    <TableCell>
                      {item.routed_to === "google_review" ? (
                        <Badge variant="success">Google Review</Badge>
                      ) : (
                        <Badge variant="secondary">Privado</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ─── Modal ───────────────────────────────────────────────────────── */}
      <SendSurveyModal
        open={sendModalOpen}
        onClose={() => setSendModalOpen(false)}
      />
    </div>
  );
}
