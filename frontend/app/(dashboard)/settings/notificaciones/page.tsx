"use client";

import * as React from "react";
import { Bell } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useNotificationPreferences,
  useUpdatePreferences,
  type PreferenceUpdate,
} from "@/lib/hooks/use-notifications";
import { cn } from "@/lib/utils";

// ─── Constants ───────────────────────────────────────────────────────────────

const EVENT_TYPE_LABELS: Record<string, string> = {
  appointment_reminder: "Recordatorio de cita",
  appointment_confirmed: "Cita confirmada",
  appointment_cancelled: "Cita cancelada",
  payment_received: "Pago recibido",
  payment_overdue: "Pago vencido",
  treatment_plan_approved: "Plan de tratamiento aprobado",
  consent_signed: "Consentimiento firmado",
};

const EVENT_TYPE_ORDER = [
  "appointment_reminder",
  "appointment_confirmed",
  "appointment_cancelled",
  "payment_received",
  "payment_overdue",
  "treatment_plan_approved",
  "consent_signed",
];

const CHANNEL_LABELS: Record<string, string> = {
  email: "Correo",
  sms: "SMS",
  whatsapp: "WhatsApp",
};

const MUTABLE_CHANNELS = ["email", "sms", "whatsapp"] as const;

// ─── Loading skeleton ────────────────────────────────────────────────────────

function PreferencesSkeleton() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div className="space-y-1">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="border rounded-xl p-6 space-y-4">
        <Skeleton className="h-5 w-48" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div key={i} className="flex items-center justify-between">
              <Skeleton className="h-4 w-48" />
              <div className="flex gap-8">
                <Skeleton className="h-5 w-5" />
                <Skeleton className="h-5 w-5" />
                <Skeleton className="h-5 w-5" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function NotificationPreferencesPage() {
  const { data, isLoading } = useNotificationPreferences();
  const updatePrefs = useUpdatePreferences();

  function handleToggle(eventType: string, channel: string, enabled: boolean) {
    const update: PreferenceUpdate[] = [
      { event_type: eventType, channel, enabled },
    ];
    updatePrefs.mutate(update);
  }

  if (isLoading) {
    return <PreferencesSkeleton />;
  }

  const preferences = data?.preferences ?? {};

  return (
    <div className="max-w-3xl space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Preferencias de notificaciones
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Elige cómo quieres recibir cada tipo de notificación. Las notificaciones
          en la app siempre están activas.
        </p>
      </div>

      {/* Preferences matrix */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Canales por tipo de evento
          </CardTitle>
          <CardDescription>
            Marca los canales que deseas activar para cada tipo de notificación.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Column headers */}
          <div className="flex items-center border-b border-[hsl(var(--border))] pb-3 mb-3">
            <div className="flex-1 text-sm font-medium text-foreground">
              Tipo de notificación
            </div>
            <div className="flex items-center gap-0">
              {MUTABLE_CHANNELS.map((channel) => (
                <div
                  key={channel}
                  className="w-20 text-center text-xs font-medium text-[hsl(var(--muted-foreground))]"
                >
                  {CHANNEL_LABELS[channel]}
                </div>
              ))}
              <div className="w-20 text-center text-xs font-medium text-[hsl(var(--muted-foreground))]">
                En app
              </div>
            </div>
          </div>

          {/* Rows */}
          <div className="space-y-1">
            {EVENT_TYPE_ORDER.map((eventType) => {
              const prefs = preferences[eventType];
              if (!prefs) return null;

              return (
                <div
                  key={eventType}
                  className={cn(
                    "flex items-center rounded-md px-2 py-2.5",
                    "hover:bg-[hsl(var(--muted))]/50 transition-colors",
                  )}
                >
                  <div className="flex-1 text-sm text-foreground">
                    {EVENT_TYPE_LABELS[eventType] ?? eventType}
                  </div>
                  <div className="flex items-center gap-0">
                    {MUTABLE_CHANNELS.map((channel) => (
                      <div key={channel} className="w-20 flex justify-center">
                        <Checkbox
                          checked={prefs[channel] ?? false}
                          onCheckedChange={(checked) =>
                            handleToggle(eventType, channel, Boolean(checked))
                          }
                          disabled={updatePrefs.isPending}
                          aria-label={`${EVENT_TYPE_LABELS[eventType]} - ${CHANNEL_LABELS[channel]}`}
                        />
                      </div>
                    ))}
                    {/* In-app — always on, disabled */}
                    <div className="w-20 flex justify-center">
                      <Checkbox
                        checked={true}
                        disabled
                        aria-label={`${EVENT_TYPE_LABELS[eventType]} - En app (siempre activo)`}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-4 text-center">
            Las notificaciones en la app no se pueden desactivar. SMS y WhatsApp
            requieren integración activa.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
