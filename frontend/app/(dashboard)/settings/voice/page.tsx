"use client";

import * as React from "react";
import { Mic, Lock, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/hooks/use-auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface VoiceSettings {
  is_enabled: boolean;
  /** Maximum dictation session length in seconds (60–3600) */
  max_session_duration_seconds: number;
  /** Maximum sessions per doctor per hour (1–200) */
  max_sessions_per_hour: number;
}

// ─── Query key ────────────────────────────────────────────────────────────────

const VOICE_SETTINGS_KEY = ["voice-settings"] as const;

// ─── Hooks ────────────────────────────────────────────────────────────────────

function useVoiceSettings() {
  return useQuery({
    queryKey: VOICE_SETTINGS_KEY,
    queryFn: () => apiGet<VoiceSettings>("/voice/settings"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

function useUpdateVoiceSettings() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Partial<VoiceSettings>) =>
      apiPut<VoiceSettings>("/voice/settings", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: VOICE_SETTINGS_KEY });
      success(
        "Configuración de voz actualizada",
        "Los cambios se aplicarán en la próxima sesión de dictado.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo guardar la configuración. Inténtalo de nuevo.";
      error("Error al guardar configuración de voz", message);
    },
  });
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function VoiceSettingsSkeleton() {
  return (
    <div className="max-w-2xl space-y-6">
      <div className="space-y-1">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="rounded-xl border p-6 space-y-5">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </div>
  );
}

// ─── Toggle switch primitive (no Radix required) ──────────────────────────────

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  label: string;
}

function ToggleSwitch({ checked, onChange, disabled, id, label }: ToggleSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      id={id}
      aria-checked={checked}
      aria-label={label}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent",
        "transition-colors duration-200 ease-in-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
        checked ? "bg-primary-600" : "bg-[hsl(var(--muted-foreground))]/40",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm",
          "transition-transform duration-200",
          checked ? "translate-x-5" : "translate-x-0",
        )}
      />
    </button>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function VoiceSettingsPage() {
  const { has_role, has_feature } = useAuth();
  const isOwner = has_role("clinic_owner");
  const isFeatureActive = has_feature("voice_dictation");

  const { data: serverSettings, isLoading } = useVoiceSettings();
  const { mutate: updateSettings, isPending } = useUpdateVoiceSettings();

  // Local form state
  const [isEnabled, setIsEnabled] = React.useState(false);
  const [maxDuration, setMaxDuration] = React.useState(300);
  const [maxPerHour, setMaxPerHour] = React.useState(10);
  const [isDirty, setIsDirty] = React.useState(false);

  React.useEffect(() => {
    if (!serverSettings) return;
    setIsEnabled(serverSettings.is_enabled);
    setMaxDuration(serverSettings.max_session_duration_seconds);
    setMaxPerHour(serverSettings.max_sessions_per_hour);
    setIsDirty(false);
  }, [serverSettings]);

  function mark() {
    setIsDirty(true);
  }

  function handleSave() {
    updateSettings(
      {
        is_enabled: isEnabled,
        max_session_duration_seconds: maxDuration,
        max_sessions_per_hour: maxPerHour,
      },
      { onSuccess: () => setIsDirty(false) },
    );
  }

  if (isLoading) return <VoiceSettingsSkeleton />;

  return (
    <div className="max-w-2xl space-y-6">
      {/* ─── Page header ──────────────────────────────────────────────────── */}
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
          <Mic className="h-5 w-5 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Configuración de voz
          </h1>
          <p className="mt-0.5 text-sm text-[hsl(var(--muted-foreground))]">
            Parámetros del motor de dictado por voz (Voice-to-Odontogram).
          </p>
        </div>
      </div>

      {/* Plan gate notice — only shown when feature is not in plan */}
      {!isFeatureActive && (
        <div className="flex items-start gap-2 rounded-lg border border-warning-200 bg-warning-50 px-4 py-3 text-sm text-accent-700 dark:border-accent-700/40 dark:bg-accent-900/20 dark:text-accent-300">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            El módulo de voz no está incluido en tu plan actual. Actualiza a{" "}
            <strong>Pro</strong> o <strong>Clínica</strong> para habilitarlo.
          </span>
        </div>
      )}

      {/* Read-only notice for non-owners */}
      {!isOwner && (
        <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
          <Lock className="h-4 w-4 shrink-0" />
          Solo el propietario de la clínica puede modificar esta configuración.
        </div>
      )}

      {/* ─── Main settings card ──────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parámetros de sesión</CardTitle>
          <CardDescription>
            Controla cómo los médicos pueden usar el dictado por voz en su flujo
            clínico diario.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Enable / disable toggle */}
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label
                htmlFor="voice-enabled"
                className="text-sm font-medium leading-none"
              >
                Habilitar dictado por voz
              </Label>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Cuando está activo, los médicos pueden dictar notas clínicas y
                condiciones del odontograma.
              </p>
            </div>
            <ToggleSwitch
              id="voice-enabled"
              label="Habilitar dictado por voz"
              checked={isEnabled}
              onChange={(val) => {
                setIsEnabled(val);
                mark();
              }}
              disabled={!isOwner || !isFeatureActive}
            />
          </div>

          <Separator />

          {/* Max session duration */}
          <div className="space-y-2">
            <Label htmlFor="max-duration" className="text-sm font-medium">
              Duración máxima de sesión
            </Label>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Tiempo máximo en segundos que puede durar una sesión de dictado
              continua (60 – 3 600 s).
            </p>
            <div className="flex items-center gap-3">
              <Input
                id="max-duration"
                type="number"
                min={60}
                max={3600}
                step={30}
                value={maxDuration}
                onChange={(e) => {
                  setMaxDuration(Number(e.target.value));
                  mark();
                }}
                disabled={!isOwner || !isFeatureActive || !isEnabled}
                className="w-36"
              />
              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                segundos ({Math.round(maxDuration / 60)} min)
              </span>
            </div>
            {/* Visual range slider */}
            <input
              type="range"
              min={60}
              max={3600}
              step={30}
              value={maxDuration}
              onChange={(e) => {
                setMaxDuration(Number(e.target.value));
                mark();
              }}
              disabled={!isOwner || !isFeatureActive || !isEnabled}
              aria-label="Duración máxima de sesión"
              className={cn(
                "h-1.5 w-full cursor-pointer appearance-none rounded-full",
                "accent-primary-600",
                (!isOwner || !isFeatureActive || !isEnabled) && "opacity-40 cursor-not-allowed",
              )}
            />
            <div className="flex justify-between text-xs text-[hsl(var(--muted-foreground))]">
              <span>1 min</span>
              <span>60 min</span>
            </div>
          </div>

          <Separator />

          {/* Max sessions per hour */}
          <div className="space-y-2">
            <Label htmlFor="max-per-hour" className="text-sm font-medium">
              Sesiones máximas por hora
            </Label>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Límite de sesiones de dictado que un médico puede iniciar en 60
              minutos para controlar el uso de la API de voz (1 – 200).
            </p>
            <div className="flex items-center gap-3">
              <Input
                id="max-per-hour"
                type="number"
                min={1}
                max={200}
                value={maxPerHour}
                onChange={(e) => {
                  setMaxPerHour(Number(e.target.value));
                  mark();
                }}
                disabled={!isOwner || !isFeatureActive || !isEnabled}
                className="w-28"
              />
              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                sesiones / hora
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ─── Info note ───────────────────────────────────────────────────── */}
      <div className="flex items-start gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/40 px-4 py-3 text-xs text-[hsl(var(--muted-foreground))]">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          El dictado por voz usa Whisper + IA para transcribir y mapear condiciones
          al odontograma. El audio se procesa en tiempo real y no se almacena.
          Revisa la política de privacidad para más detalles.
        </span>
      </div>

      <Separator />

      {/* ─── Save button ─────────────────────────────────────────────────── */}
      {isOwner && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            {isDirty
              ? "Tienes cambios sin guardar."
              : "La configuración está actualizada."}
          </p>
          <Button
            type="button"
            onClick={handleSave}
            disabled={isPending || !isDirty}
          >
            {isPending ? "Guardando..." : "Guardar configuración"}
          </Button>
        </div>
      )}
    </div>
  );
}
