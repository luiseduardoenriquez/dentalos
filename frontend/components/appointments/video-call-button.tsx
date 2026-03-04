"use client";

import * as React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Video, ExternalLink, Loader2 } from "lucide-react";
import { apiPost, apiGet } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface VideoSession {
  session_id: string;
  join_url_doctor: string;
  join_url_patient: string;
  status: string;
  expires_at: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

interface VideoCallButtonProps {
  appointmentId: string;
  className?: string;
  size?: "default" | "sm" | "lg" | "icon";
  variant?: "default" | "outline" | "secondary" | "ghost";
}

export function VideoCallButton({
  appointmentId,
  className,
  size = "sm",
  variant = "outline",
}: VideoCallButtonProps) {
  const [sessionReady, setSessionReady] = React.useState(false);
  const [sessionUrl, setSessionUrl] = React.useState<string | null>(null);

  // Try to fetch existing session first
  const { data: existingSession, isLoading: isCheckingSession } = useQuery({
    queryKey: ["video-session", appointmentId],
    queryFn: () =>
      apiGet<VideoSession>(`/telemedicine/appointments/${appointmentId}/video-session`),
    retry: false,
    staleTime: 5 * 60_000,
  });

  // Set session URL if existing session found
  React.useEffect(() => {
    if (existingSession?.join_url_doctor) {
      setSessionUrl(existingSession.join_url_doctor);
      setSessionReady(true);
    }
  }, [existingSession]);

  // Create new session mutation
  const { mutate: createSession, isPending: isCreating } = useMutation({
    mutationFn: () =>
      apiPost<VideoSession>(`/telemedicine/appointments/${appointmentId}/video-session`),
    onSuccess: (data) => {
      setSessionUrl(data.join_url_doctor);
      setSessionReady(true);
      // Open immediately after creation
      window.open(data.join_url_doctor, "_blank", "noopener,noreferrer");
    },
  });

  function handleClick() {
    if (sessionReady && sessionUrl) {
      // Session exists — open join URL
      window.open(sessionUrl, "_blank", "noopener,noreferrer");
    } else {
      // Create a new session
      createSession();
    }
  }

  const isLoading = isCheckingSession || isCreating;
  const label = sessionReady ? "Unirse a Videollamada" : "Iniciar Videollamada";

  return (
    <Button
      variant={variant}
      size={size}
      disabled={isLoading}
      onClick={handleClick}
      className={cn("gap-1.5", className)}
    >
      {isLoading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : sessionReady ? (
        <ExternalLink className="h-3.5 w-3.5" />
      ) : (
        <Video className="h-3.5 w-3.5" />
      )}
      {isLoading ? "Preparando..." : label}
    </Button>
  );
}
