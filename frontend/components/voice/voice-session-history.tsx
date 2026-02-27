"use client";

import * as React from "react";
import { Clock, Mic } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useVoiceSessions, type VoiceSession } from "@/lib/hooks/use-voice";
import { formatDateTime } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Maps context values to Spanish labels */
const CONTEXT_LABELS: Record<VoiceSession["context"], string> = {
  odontogram: "Odontograma",
  evolution: "Evolucion",
  examination: "Examen",
};

/** Maps status values to badge variants */
const STATUS_CONFIG: Record<VoiceSession["status"], { label: string; variant: "default" | "warning" | "success" }> = {
  recording: { label: "Grabando", variant: "warning" },
  processing: { label: "Procesando", variant: "default" },
  applied: { label: "Aplicado", variant: "success" },
};

// ─── Types ────────────────────────────────────────────────────────────────────

interface VoiceSessionHistoryProps {
  /** Patient ID to fetch voice sessions for */
  patientId: string;
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function SessionSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Session Card ─────────────────────────────────────────────────────────────

function SessionCard({ session }: { session: VoiceSession }) {
  const statusConfig = STATUS_CONFIG[session.status];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-4">
          {/* Left: session info */}
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/30">
              <Mic className="h-4 w-4 text-primary-600 dark:text-primary-400" />
            </div>

            <div className="min-w-0">
              {/* Date and time */}
              <div className="flex items-center gap-2">
                <Clock className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                <span className="text-sm font-medium text-foreground">
                  {formatDateTime(session.created_at)}
                </span>
              </div>

              {/* Context label */}
              <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
                Contexto: {CONTEXT_LABELS[session.context]}
              </p>
            </div>
          </div>

          {/* Right: status badge */}
          <Badge variant={statusConfig.variant} className="shrink-0">
            {statusConfig.label}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Displays a list of past voice sessions for a patient.
 * Sessions are fetched via useVoiceSessions and sorted by created_at descending (most recent first).
 */
export function VoiceSessionHistory({ patientId }: VoiceSessionHistoryProps) {
  const { data, isLoading } = useVoiceSessions(patientId);

  // Sort sessions by created_at descending (most recent first)
  const sortedSessions = React.useMemo(() => {
    if (!data?.items) return [];
    return [...data.items].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  }, [data?.items]);

  return (
    <div className="space-y-4">
      <CardHeader className="px-0 pb-2">
        <CardTitle className="text-base">Historial de sesiones de voz</CardTitle>
      </CardHeader>

      {/* Loading state */}
      {isLoading && <SessionSkeleton />}

      {/* Empty state */}
      {!isLoading && sortedSessions.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Mic className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-40" />
            <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
              No hay sesiones de voz registradas para este paciente.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Session list */}
      {!isLoading && sortedSessions.length > 0 && (
        <div className="space-y-2">
          {sortedSessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}

          {/* Pagination info */}
          {data && data.total > data.page_size && (
            <p className="pt-2 text-center text-xs text-[hsl(var(--muted-foreground))]">
              Mostrando {sortedSessions.length} de {data.total} sesiones
            </p>
          )}
        </div>
      )}
    </div>
  );
}
