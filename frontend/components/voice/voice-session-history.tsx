"use client";

import * as React from "react";
import { ChevronDown, Clock, Mic, User, Volume2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useVoiceSessions,
  useVoiceSessionDetail,
  type VoiceSession,
  type TranscriptionChunk,
} from "@/lib/hooks/use-voice";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { VoiceClinicalNoteRecorder } from "@/components/voice/voice-clinical-note-recorder";
import { SOAPNoteReviewPanel } from "@/components/voice/soap-note-review-panel";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Maps context values to Spanish labels */
const CONTEXT_LABELS: Record<VoiceSession["context"], string> = {
  odontogram: "Odontograma",
  evolution: "Evolucion",
  examination: "Examen",
};

/** Maps status values to badge variants */
const STATUS_CONFIG: Record<
  string,
  { label: string; variant: "default" | "warning" | "success" | "secondary" }
> = {
  active: { label: "Activa", variant: "warning" },
  applied: { label: "Aplicado", variant: "success" },
  expired: { label: "Expirada", variant: "secondary" },
  feedback_received: { label: "Con feedback", variant: "default" },
};

const FALLBACK_STATUS = { label: "Desconocido", variant: "secondary" as const };

const CHUNK_STATUS_CONFIG: Record<
  string,
  { label: string; variant: "default" | "warning" | "success" | "destructive" | "secondary" }
> = {
  pending: { label: "Pendiente", variant: "secondary" },
  processing: { label: "Procesando", variant: "warning" },
  completed: { label: "Completado", variant: "success" },
  failed: { label: "Fallido", variant: "destructive" },
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

// ─── Transcription Chunk ────────────────────────────────────────────────────

function TranscriptionChunkCard({ chunk }: { chunk: TranscriptionChunk }) {
  const statusConfig = CHUNK_STATUS_CONFIG[chunk.status] ?? FALLBACK_STATUS;

  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/30 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
          Fragmento {chunk.chunk_index + 1}
          {chunk.duration_seconds != null && (
            <> &middot; {chunk.duration_seconds.toFixed(1)}s</>
          )}
        </span>
        <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
      </div>

      {/* Audio player */}
      {chunk.audio_url && (
        <div className="flex items-center gap-2">
          <Volume2 className="h-3.5 w-3.5 shrink-0 text-primary-500" />
          <audio
            controls
            preload="none"
            src={chunk.audio_url}
            className="h-8 w-full"
          />
        </div>
      )}

      {/* Transcription text */}
      {chunk.text && (
        <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
          {chunk.text}
        </p>
      )}

      {chunk.status === "pending" && (
        <p className="text-xs italic text-[hsl(var(--muted-foreground))]">
          Esperando transcripcion...
        </p>
      )}
    </div>
  );
}

// ─── Session Detail (expanded) ──────────────────────────────────────────────

function SessionDetail({ sessionId }: { sessionId: string }) {
  const { data: detail, isLoading } = useVoiceSessionDetail(sessionId);
  const [clinicalNoteId, setClinicalNoteId] = React.useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-3 pt-3 border-t border-[hsl(var(--border))]">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (!detail) return null;

  const transcriptions = detail.transcriptions ?? [];
  const hasCompletedTranscriptions = transcriptions.some(
    (t) => t.status === "completed" && t.text,
  );
  const isEvolutionContext = detail.context === "evolution";

  return (
    <div className="space-y-3 pt-3 border-t border-[hsl(var(--border))]">
      {/* Patient name */}
      {detail.patient_name && (
        <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
          <User className="h-3.5 w-3.5" />
          <span>Paciente: {detail.patient_name}</span>
        </div>
      )}

      {/* Transcription chunks */}
      {transcriptions.length === 0 ? (
        <p className="text-sm text-[hsl(var(--muted-foreground))] italic">
          No hay fragmentos de audio en esta sesion.
        </p>
      ) : (
        <div className="space-y-2">
          {transcriptions.map((chunk) => (
            <TranscriptionChunkCard key={chunk.id} chunk={chunk} />
          ))}
        </div>
      )}

      {/* AI-03: Structure as SOAP note (only for evolution context with completed transcriptions) */}
      {isEvolutionContext && hasCompletedTranscriptions && !clinicalNoteId && (
        <VoiceClinicalNoteRecorder
          sessionId={sessionId}
          onNoteCreated={(noteId) => setClinicalNoteId(noteId)}
        />
      )}

      {/* AI-03: SOAP note review panel */}
      {clinicalNoteId && (
        <SOAPNoteReviewPanel noteId={clinicalNoteId} />
      )}
    </div>
  );
}

// ─── Session Card ─────────────────────────────────────────────────────────────

function SessionCard({ session }: { session: VoiceSession }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const statusConfig = STATUS_CONFIG[session.status] ?? FALLBACK_STATUS;

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => setIsExpanded((prev) => !prev)}
    >
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

              {/* Context + doctor name */}
              <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
                {CONTEXT_LABELS[session.context]}
                {session.doctor_name && <> &middot; Dr. {session.doctor_name}</>}
              </p>
            </div>
          </div>

          {/* Right: status badge + chevron */}
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
            <ChevronDown
              className={cn(
                "h-4 w-4 text-[hsl(var(--muted-foreground))] transition-transform duration-200",
                isExpanded && "rotate-180",
              )}
            />
          </div>
        </div>

        {/* Expanded detail — stop clicks from toggling the card */}
        {isExpanded && (
          <div onClick={(e) => e.stopPropagation()}>
            <SessionDetail sessionId={session.id} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Displays a list of past voice sessions for a patient.
 * Sessions are fetched via useVoiceSessions and sorted by created_at descending (most recent first).
 * Each session card is expandable — clicking shows transcription chunks with audio playback.
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
