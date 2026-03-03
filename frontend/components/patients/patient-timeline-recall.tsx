"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Mail, MousePointerClick, Eye, CalendarCheck, Megaphone } from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface RecallEvent {
  id: string;
  event_type: "campaign_sent" | "email_opened" | "link_clicked" | "appointment_booked" | "campaign_created";
  campaign_name: string;
  occurred_at: string;
  metadata: Record<string, string>;
}

interface RecallTimelineResponse {
  items: RecallEvent[];
  total: number;
}

const EVENT_CONFIG: Record<string, { icon: React.ComponentType<{ className?: string }>; label: string; color: string }> = {
  campaign_sent: { icon: Mail, label: "Campaña enviada", color: "bg-blue-500" },
  email_opened: { icon: Eye, label: "Email abierto", color: "bg-green-500" },
  link_clicked: { icon: MousePointerClick, label: "Enlace visitado", color: "bg-amber-500" },
  appointment_booked: { icon: CalendarCheck, label: "Cita agendada", color: "bg-emerald-600" },
  campaign_created: { icon: Megaphone, label: "Campaña creada", color: "bg-purple-500" },
};

interface PatientTimelineRecallProps {
  patientId: string;
}

export function PatientTimelineRecall({ patientId }: PatientTimelineRecallProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["patient_recall_timeline", patientId],
    queryFn: () =>
      apiGet<RecallTimelineResponse>(`/patients/${patientId}/recall-timeline`),
    enabled: Boolean(patientId),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Megaphone className="h-4 w-4 text-primary-600" />
            Campañas de reactivación
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-start gap-3">
              <Skeleton className="h-6 w-6 rounded-full" />
              <div className="space-y-1 flex-1">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-32" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  const events = data?.items ?? [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Megaphone className="h-4 w-4 text-primary-600" />
          Campañas de reactivación
          {events.length > 0 && (
            <Badge variant="secondary" className="text-xs ml-auto">
              {events.length}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
            Este paciente no ha participado en campañas de reactivación.
          </p>
        ) : (
          <div className="relative space-y-0">
            {events.map((event, index) => {
              const config = EVENT_CONFIG[event.event_type] ?? EVENT_CONFIG.campaign_sent;
              const Icon = config.icon;
              const isLast = index === events.length - 1;

              return (
                <div key={event.id} className="flex items-start gap-3 pb-4 relative">
                  {/* Timeline connector line */}
                  {!isLast && (
                    <div className="absolute left-3 top-6 bottom-0 w-px bg-[hsl(var(--border))]" />
                  )}
                  {/* Icon dot */}
                  <div
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full z-10",
                      config.color,
                    )}
                  >
                    <Icon className="h-3 w-3 text-white" />
                  </div>
                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{config.label}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {event.campaign_name} · {formatDateTime(event.occurred_at)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
