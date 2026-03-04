"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Video,
  Mic,
  Camera,
  ExternalLink,
  Loader2,
  AlertCircle,
  Clock,
} from "lucide-react";
import { apiGet } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface VideoSessionJoin {
  session_id: string;
  appointment_id: string;
  join_url_patient: string;
  doctor_name: string;
  scheduled_at: string | null;
  status: string;
  expires_at: string;
}

// ─── Waiting room checklist ───────────────────────────────────────────────────

const CHECKLIST_ITEMS = [
  { icon: Camera, label: "Habilita tu cámara cuando se te solicite" },
  { icon: Mic, label: "Asegúrate de que tu micrófono esté habilitado" },
  { icon: Video, label: "Usa una conexión WiFi estable para mejor calidad" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalVideoPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params?.sessionId ?? "";

  const [joined, setJoined] = React.useState(false);

  const { data: session, isLoading, isError, refetch } = useQuery({
    queryKey: ["portal-video-session", sessionId],
    queryFn: () =>
      apiGet<VideoSessionJoin>(`/telemedicine/portal/video-sessions/${sessionId}/join`),
    retry: false,
    staleTime: 5 * 60_000,
  });

  function handleJoin() {
    if (session?.join_url_patient) {
      setJoined(true);
      window.open(session.join_url_patient, "_blank", "noopener,noreferrer");
    }
  }

  // ─── Loading state ─────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--background))] px-4">
        <div className="text-center space-y-3">
          <Loader2 className="mx-auto h-10 w-10 animate-spin text-primary-600" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Preparando tu consulta virtual...
          </p>
        </div>
      </div>
    );
  }

  // ─── Error state ───────────────────────────────────────────────────────────

  if (isError || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--background))] px-4">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
              <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
            </div>
          </div>
          <div className="space-y-1">
            <h1 className="text-lg font-semibold text-foreground">
              Sesión no disponible
            </h1>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              No encontramos tu consulta virtual. Es posible que el enlace haya
              expirado o que la cita aún no haya sido configurada.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  // ─── Waiting room ──────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--background))] px-4 py-8">
      <div className="w-full max-w-sm space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="mx-auto h-16 w-16 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
            <Video className="h-8 w-8 text-primary-600" />
          </div>
          <h1 className="text-xl font-bold text-foreground">
            Consulta Virtual
          </h1>
          <p className="text-[hsl(var(--muted-foreground))] text-sm">
            Tu doctor te está esperando
          </p>
        </div>

        {/* Session info */}
        <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 p-4 space-y-3">
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-50 dark:bg-primary-900/30 shrink-0">
              <Video className="h-4 w-4 text-primary-600" />
            </div>
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Doctor</p>
              <p className="text-sm font-semibold text-foreground">
                {session.doctor_name}
              </p>
            </div>
          </div>

          {session.scheduled_at && (
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-50 dark:bg-primary-900/30 shrink-0">
                <Clock className="h-4 w-4 text-primary-600" />
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Fecha y hora</p>
                <p className="text-sm font-semibold text-foreground">
                  {formatDateTime(session.scheduled_at)}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Checklist */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
            Antes de entrar
          </p>
          <ul className="space-y-2">
            {CHECKLIST_ITEMS.map(({ icon: Icon, label }, i) => (
              <li key={i} className="flex items-center gap-2.5 text-sm text-foreground">
                <Icon className="h-4 w-4 text-primary-600 shrink-0" />
                {label}
              </li>
            ))}
          </ul>
        </div>

        {/* Join button */}
        <Button
          size="lg"
          className="w-full gap-2"
          onClick={handleJoin}
        >
          {joined ? (
            <>
              <ExternalLink className="h-4 w-4" />
              Abrir consulta de nuevo
            </>
          ) : (
            <>
              <Video className="h-4 w-4" />
              Unirse a la consulta
            </>
          )}
        </Button>

        {joined && (
          <p className="text-center text-xs text-[hsl(var(--muted-foreground))]">
            Se abrió la consulta en una nueva pestaña. Si no se abrió, haz clic
            en el botón de arriba.
          </p>
        )}

        <p className="text-center text-xs text-[hsl(var(--muted-foreground))]">
          Esta sesión expira el{" "}
          {formatDateTime(session.expires_at)}
        </p>
      </div>
    </div>
  );
}
