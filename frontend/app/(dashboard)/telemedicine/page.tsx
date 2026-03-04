"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Video,
  RefreshCw,
  AlertCircle,
  Clock,
  ExternalLink,
} from "lucide-react";
import { apiGet } from "@/lib/api-client";
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
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatDateTime, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type VideoSessionStatus = "created" | "waiting" | "active" | "ended";

interface VideoSession {
  id: string;
  appointment_id: string;
  patient_name: string;
  doctor_name: string;
  scheduled_at: string | null;
  status: VideoSessionStatus;
  duration_minutes: number | null;
  created_at: string;
  join_url_doctor: string;
}

interface VideoSessionListResponse {
  items: VideoSession[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<VideoSessionStatus, string> = {
  created: "Creada",
  waiting: "En espera",
  active: "En curso",
  ended: "Finalizada",
};

const STATUS_FILTERS: Array<{ value: VideoSessionStatus | "all"; label: string }> = [
  { value: "all", label: "Todas" },
  { value: "created", label: "Creada" },
  { value: "waiting", label: "En espera" },
  { value: "active", label: "En curso" },
  { value: "ended", label: "Finalizada" },
];

// ─── Status badge ─────────────────────────────────────────────────────────────

function VideoStatusBadge({ status }: { status: VideoSessionStatus }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-medium",
        status === "created" &&
          "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
        status === "waiting" &&
          "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
        status === "active" &&
          "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
        status === "ended" &&
          "bg-slate-50 text-slate-600 border-slate-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700",
      )}
    >
      {STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4, 5].map((i) => (
        <Skeleton key={i} className="h-12 w-full rounded" />
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TelemedicinePage() {
  const [page, setPage] = React.useState(1);
  const [statusFilter, setStatusFilter] = React.useState<VideoSessionStatus | "all">("all");
  const pageSize = 20;

  const queryKey = ["video-sessions", page, pageSize, statusFilter];

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey,
    queryFn: () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (statusFilter !== "all") params.set("status", statusFilter);
      return apiGet<VideoSessionListResponse>(`/telemedicine/sessions?${params}`);
    },
    staleTime: 60_000,
  });

  const sessions = data?.items ?? [];
  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  // Reset page on filter change
  React.useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Telemedicina
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Gestiona las consultas virtuales de la clínica.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isLoading && "animate-spin")} />
          Actualizar
        </Button>
      </div>

      {/* ─── Filter tabs ─────────────────────────────────────────────────── */}
      <div className="flex gap-1.5 flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setStatusFilter(f.value)}
            className={cn(
              "rounded-full px-3 py-1 text-sm font-medium transition-colors",
              statusFilter === f.value
                ? "bg-primary-600 text-white"
                : "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))]/80",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ─── Sessions table ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="h-4 w-4 text-primary-600" />
            Sesiones de video
          </CardTitle>
          <CardDescription>
            {data
              ? `${data.total.toLocaleString("es-CO")} sesión${data.total !== 1 ? "es" : ""} registrada${data.total !== 1 ? "s" : ""}`
              : "Cargando..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton />
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <AlertCircle className="h-7 w-7 text-red-500" />
              <p className="text-sm text-red-600 dark:text-red-400">
                Error al cargar las sesiones.
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Reintentar
              </Button>
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-14 gap-3 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[hsl(var(--muted))]">
                <Video className="h-7 w-7 text-[hsl(var(--muted-foreground))] opacity-60" />
              </div>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No hay sesiones de video con ese filtro.
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Paciente</TableHead>
                    <TableHead>Doctor</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Programada</TableHead>
                    <TableHead className="text-right">Duración</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell className="font-medium text-foreground text-sm">
                        {session.patient_name}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {session.doctor_name}
                      </TableCell>
                      <TableCell>
                        <VideoStatusBadge status={session.status} />
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                        {session.scheduled_at ? (
                          formatDateTime(session.scheduled_at)
                        ) : (
                          <span className="italic">No programada</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums">
                        {session.duration_minutes != null ? (
                          <span className="flex items-center justify-end gap-1 text-[hsl(var(--muted-foreground))]">
                            <Clock className="h-3 w-3" />
                            {session.duration_minutes} min
                          </span>
                        ) : (
                          <span className="text-[hsl(var(--muted-foreground))]">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          {(session.status === "created" ||
                            session.status === "waiting" ||
                            session.status === "active") && (
                            <a
                              href={session.join_url_doctor}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-7 px-2 text-xs gap-1"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Entrar
                              </Button>
                            </a>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Anterior
                  </Button>
                  <span className="text-sm text-[hsl(var(--muted-foreground))]">
                    Página {page} de {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Siguiente
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
