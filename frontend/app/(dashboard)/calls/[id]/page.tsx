"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Phone,
  PhoneIncoming,
  PhoneOutgoing,
  Clock,
  Calendar,
  User,
  FileText,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDate } from "@/lib/utils";
import {
  useCallDetail,
  useUpdateCallNotes,
} from "@/lib/hooks/use-calls";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  completed: "Completada",
  missed: "Perdida",
  in_progress: "En curso",
  ringing: "Sonando",
  voicemail: "Buzón de voz",
};

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  missed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  in_progress: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  ringing: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  voicemail: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300",
};

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds <= 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length <= 4) return phone;
  return `***${digits.slice(-4)}`;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CallDetailPage() {
  const params = useParams();
  const callId = params.id as string;

  const { data: call, isLoading, isError } = useCallDetail(callId);
  const updateNotes = useUpdateCallNotes(callId);

  const [notes, setNotes] = React.useState("");
  const [notesDirty, setNotesDirty] = React.useState(false);

  // Sync notes from server data
  React.useEffect(() => {
    if (call && !notesDirty) {
      setNotes(call.notes ?? "");
    }
  }, [call, notesDirty]);

  function handleSaveNotes() {
    updateNotes.mutate(
      { notes },
      { onSuccess: () => setNotesDirty(false) },
    );
  }

  if (isLoading) {
    return (
      <div className="p-6 max-w-2xl space-y-6">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  if (isError || !call) {
    return (
      <div className="p-6 space-y-4">
        <Link
          href="/calls"
          className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver a llamadas
        </Link>
        <Card>
          <CardContent className="py-10 text-center text-[hsl(var(--muted-foreground))]">
            No se pudo cargar el detalle de la llamada.
          </CardContent>
        </Card>
      </div>
    );
  }

  const DirectionIcon = call.direction === "inbound" ? PhoneIncoming : PhoneOutgoing;

  return (
    <div className="p-6 max-w-2xl space-y-6">
      {/* Back link */}
      <Link
        href="/calls"
        className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" />
        Volver a llamadas
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/30">
          <DirectionIcon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground">
            Llamada {call.direction === "inbound" ? "entrante" : "saliente"}
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {maskPhone(call.phone_number)}
          </p>
        </div>
        <Badge className={cn("ml-auto", STATUS_COLORS[call.status] ?? "")}>
          {STATUS_LABELS[call.status] ?? call.status}
        </Badge>
      </div>

      {/* Call info card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Detalles de la llamada</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-start gap-2">
              <Calendar className="h-4 w-4 mt-0.5 text-[hsl(var(--muted-foreground))]" />
              <div>
                <dt className="text-xs text-[hsl(var(--muted-foreground))]">Fecha</dt>
                <dd className="text-foreground">
                  {call.started_at
                    ? formatDate(call.started_at, {
                        dateStyle: "long",
                        timeStyle: "short",
                      } as Intl.DateTimeFormatOptions)
                    : formatDate(call.created_at)}
                </dd>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Clock className="h-4 w-4 mt-0.5 text-[hsl(var(--muted-foreground))]" />
              <div>
                <dt className="text-xs text-[hsl(var(--muted-foreground))]">Duración</dt>
                <dd className="text-foreground tabular-nums">
                  {formatDuration(call.duration_seconds)}
                </dd>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Phone className="h-4 w-4 mt-0.5 text-[hsl(var(--muted-foreground))]" />
              <div>
                <dt className="text-xs text-[hsl(var(--muted-foreground))]">Dirección</dt>
                <dd className="text-foreground">
                  {call.direction === "inbound" ? "Entrante" : "Saliente"}
                </dd>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <User className="h-4 w-4 mt-0.5 text-[hsl(var(--muted-foreground))]" />
              <div>
                <dt className="text-xs text-[hsl(var(--muted-foreground))]">Paciente</dt>
                <dd className="text-foreground">
                  {call.patient_id ? (
                    <Link
                      href={`/patients/${call.patient_id}`}
                      className="text-primary-600 hover:underline"
                    >
                      Ver paciente
                    </Link>
                  ) : (
                    <span className="text-[hsl(var(--muted-foreground))]">No asignado</span>
                  )}
                </dd>
              </div>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Notes section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Notas
          </CardTitle>
          <CardDescription>
            Agrega o edita las notas de esta llamada.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            value={notes}
            onChange={(e) => {
              setNotes(e.target.value);
              setNotesDirty(true);
            }}
            placeholder="Escribe notas sobre esta llamada..."
            rows={5}
            className={cn(
              "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
              "px-3 py-2 text-sm text-foreground placeholder:text-[hsl(var(--muted-foreground))]",
              "focus:outline-none focus:ring-2 focus:ring-primary-600 resize-y",
            )}
          />
          <div className="flex justify-end">
            <Button
              size="sm"
              disabled={!notesDirty || updateNotes.isPending}
              onClick={handleSaveNotes}
            >
              {updateNotes.isPending ? "Guardando..." : "Guardar notas"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
