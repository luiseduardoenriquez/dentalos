"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, CheckCircle2, Star } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReputationSettings {
  google_review_url: string | null;
  review_score_threshold: number;
  survey_delay_hours: number;
  channels: {
    whatsapp: boolean;
    sms: boolean;
    email: boolean;
  };
}

// ─── Default Values ───────────────────────────────────────────────────────────

const DEFAULT_SETTINGS: ReputationSettings = {
  google_review_url: "",
  review_score_threshold: 4,
  survey_delay_hours: 2,
  channels: {
    whatsapp: true,
    sms: false,
    email: true,
  },
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReputationSettingsPage() {
  const queryClient = useQueryClient();
  const [saved, setSaved] = React.useState(false);
  const [form, setForm] = React.useState<ReputationSettings>(DEFAULT_SETTINGS);

  const { data: settingsData, isLoading, isError } = useQuery({
    queryKey: ["settings", "reputation"],
    queryFn: () => apiGet<ReputationSettings>("/settings/reputation"),
    staleTime: 2 * 60_000,
  });

  // Populate form when data loads
  React.useEffect(() => {
    if (!settingsData) return;
    setForm({
      google_review_url: settingsData.google_review_url ?? "",
      review_score_threshold: settingsData.review_score_threshold ?? 4,
      survey_delay_hours: settingsData.survey_delay_hours ?? 2,
      channels: {
        whatsapp: settingsData.channels?.whatsapp ?? true,
        sms: settingsData.channels?.sms ?? false,
        email: settingsData.channels?.email ?? true,
      },
    });
  }, [settingsData]);

  const { mutate: saveSettings, isPending: isSaving } = useMutation({
    mutationFn: (payload: ReputationSettings) =>
      apiPut<ReputationSettings>("/settings/reputation", payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["settings", "reputation"], updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    saveSettings(form);
  }

  function handleChannelToggle(channel: keyof ReputationSettings["channels"]) {
    setForm((prev) => ({
      ...prev,
      channels: {
        ...prev.channels,
        [channel]: !prev.channels[channel],
      },
    }));
  }

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-2xl animate-pulse">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-36 rounded-xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          Error al cargar la configuración de reputación.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Configuración de reputación
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Configura cómo se enrutan las encuestas de satisfacción y la integración
          con Google Reviews.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* ─── Google Reviews ──────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Google Reviews</CardTitle>
            <CardDescription>
              Los pacientes con calificación igual o superior al umbral serán
              dirigidos a dejar una reseña en Google.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="google-url">URL de Google Review</Label>
              <Input
                id="google-url"
                type="url"
                placeholder="https://g.page/r/your-clinic-id/review"
                value={form.google_review_url ?? ""}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    google_review_url: e.target.value,
                  }))
                }
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Copia el enlace desde Google Business Profile → Obtener enlace de reseña.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="score-threshold">
                Umbral de calificación para Google Review
              </Label>
              <div className="flex items-center gap-3">
                <Input
                  id="score-threshold"
                  type="number"
                  min={1}
                  max={5}
                  className="w-20"
                  value={form.review_score_threshold}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      review_score_threshold: Math.min(
                        5,
                        Math.max(1, parseInt(e.target.value, 10) || 4),
                      ),
                    }))
                  }
                />
                <div className="flex items-center gap-0.5">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className={`h-4 w-4 ${
                        i < form.review_score_threshold
                          ? "fill-yellow-400 text-yellow-400"
                          : "fill-transparent text-slate-300"
                      }`}
                    />
                  ))}
                </div>
              </div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Pacientes con esta calificación o más serán redirigidos a Google.
                Los demás recibirán un formulario privado.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* ─── Survey Timing ──────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Envío de encuesta</CardTitle>
            <CardDescription>
              Controla cuándo se envía la encuesta después de una cita completada.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="delay-hours">Horas de espera tras la cita</Label>
              <Input
                id="delay-hours"
                type="number"
                min={0}
                max={72}
                className="w-24"
                value={form.survey_delay_hours}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    survey_delay_hours: Math.min(
                      72,
                      Math.max(0, parseInt(e.target.value, 10) || 2),
                    ),
                  }))
                }
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                La encuesta se enviará automáticamente este número de horas después
                de que la cita se marque como completada. 0 = inmediatamente.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* ─── Channels ───────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Canales de envío</CardTitle>
            <CardDescription>
              Selecciona por qué medios se enviará la encuesta.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(
                [
                  { key: "whatsapp", label: "WhatsApp" },
                  { key: "sms", label: "SMS" },
                  { key: "email", label: "Correo electrónico" },
                ] as { key: keyof ReputationSettings["channels"]; label: string }[]
              ).map(({ key, label }) => (
                <div key={key} className="flex items-center gap-3">
                  <Checkbox
                    id={`channel-${key}`}
                    checked={form.channels[key]}
                    onCheckedChange={() => handleChannelToggle(key)}
                  />
                  <Label
                    htmlFor={`channel-${key}`}
                    className="text-sm font-normal cursor-pointer"
                  >
                    {label}
                  </Label>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* ─── Actions ────────────────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={isSaving}>
            {isSaving ? "Guardando..." : "Guardar configuración"}
          </Button>
          {saved && (
            <span className="flex items-center gap-1.5 text-sm text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              Guardado
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
