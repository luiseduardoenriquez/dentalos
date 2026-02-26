"use client";

import * as React from "react";
import { Grid3X3, Lock, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/hooks/use-auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface OdontogramSettings {
  /** Display mode for the odontogram: classic grid or anatomic arch view */
  default_view: "classic" | "anatomic";
  /** Default zoom level when opening the odontogram */
  default_zoom: "full" | "quadrant";
  /** Whether to auto-save the odontogram during voice dictation sessions */
  auto_save_dictation: boolean;
  /** Custom condition color overrides keyed by condition code */
  condition_colors: Record<string, string>;
}

// ─── Query key ────────────────────────────────────────────────────────────────

const ODONTOGRAM_SETTINGS_KEY = ["settings", "odontogram"] as const;

// ─── Hooks ────────────────────────────────────────────────────────────────────

function useOdontogramSettings() {
  return useQuery({
    queryKey: ODONTOGRAM_SETTINGS_KEY,
    queryFn: () => apiGet<OdontogramSettings>("/settings/odontogram"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

function useUpdateOdontogramSettings() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: Partial<OdontogramSettings>) =>
      apiPut<OdontogramSettings>("/settings/odontogram", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ODONTOGRAM_SETTINGS_KEY });
      success(
        "Configuración del odontograma actualizada",
        "Los cambios se aplicarán al abrir el próximo odontograma.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo guardar la configuración. Inténtalo de nuevo.";
      error("Error al guardar configuración del odontograma", message);
    },
  });
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function OdontogramSettingsSkeleton() {
  return (
    <div className="max-w-2xl space-y-6">
      <div className="space-y-1">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="rounded-xl border p-6 space-y-5">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </div>
  );
}

// ─── Toggle switch primitive ───────────────────────────────────────────────────

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

export default function OdontogramSettingsPage() {
  const { has_role } = useAuth();
  const isOwner = has_role("clinic_owner");

  const { data: serverSettings, isLoading } = useOdontogramSettings();
  const { mutate: updateSettings, isPending } = useUpdateOdontogramSettings();

  // Local form state
  const [defaultView, setDefaultView] = React.useState<"classic" | "anatomic">("classic");
  const [defaultZoom, setDefaultZoom] = React.useState<"full" | "quadrant">("full");
  const [autoSaveDictation, setAutoSaveDictation] = React.useState(false);
  const [isDirty, setIsDirty] = React.useState(false);

  React.useEffect(() => {
    if (!serverSettings) return;
    setDefaultView(serverSettings.default_view);
    setDefaultZoom(serverSettings.default_zoom);
    setAutoSaveDictation(serverSettings.auto_save_dictation);
    setIsDirty(false);
  }, [serverSettings]);

  function mark() {
    setIsDirty(true);
  }

  function handleSave() {
    updateSettings(
      {
        default_view: defaultView,
        default_zoom: defaultZoom,
        auto_save_dictation: autoSaveDictation,
      },
      { onSuccess: () => setIsDirty(false) },
    );
  }

  if (isLoading) return <OdontogramSettingsSkeleton />;

  return (
    <div className="max-w-2xl space-y-6">
      {/* ─── Page header ──────────────────────────────────────────────────── */}
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
          <Grid3X3 className="h-5 w-5 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Configuración del odontograma
          </h1>
          <p className="mt-0.5 text-sm text-[hsl(var(--muted-foreground))]">
            Modo de vista, zoom predeterminado y opciones de dictado por voz.
          </p>
        </div>
      </div>

      {/* Read-only notice for non-owners */}
      {!isOwner && (
        <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
          <Lock className="h-4 w-4 shrink-0" />
          Solo el propietario de la clínica puede modificar esta configuración.
        </div>
      )}

      {/* ─── Main settings card ────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Visualización</CardTitle>
          <CardDescription>
            Controla cómo se muestra el odontograma para todos los médicos de la clínica.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Default view mode */}
          <div className="space-y-2">
            <Label htmlFor="default-view" className="text-sm font-medium">
              Modo de vista predeterminado
            </Label>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              El modo de visualización que se usa al abrir el odontograma de un paciente.
            </p>
            <Select
              value={defaultView}
              onValueChange={(val) => {
                setDefaultView(val as "classic" | "anatomic");
                mark();
              }}
              disabled={!isOwner}
            >
              <SelectTrigger id="default-view" aria-label="Modo de vista predeterminado">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="classic">Grilla clásica</SelectItem>
                <SelectItem value="anatomic">Vista anatómica</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Separator />

          {/* Default zoom level */}
          <div className="space-y-2">
            <Label htmlFor="default-zoom" className="text-sm font-medium">
              Zoom predeterminado
            </Label>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Nivel de zoom inicial al abrir el odontograma.
            </p>
            <Select
              value={defaultZoom}
              onValueChange={(val) => {
                setDefaultZoom(val as "full" | "quadrant");
                mark();
              }}
              disabled={!isOwner}
            >
              <SelectTrigger id="default-zoom" aria-label="Zoom predeterminado">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="full">Dentición completa</SelectItem>
                <SelectItem value="quadrant">Por cuadrante</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Separator />

          {/* Auto-save dictation toggle */}
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label
                htmlFor="auto-save-dictation"
                className="text-sm font-medium leading-none"
              >
                Guardar automáticamente durante el dictado
              </Label>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Cuando está activo, los cambios del odontograma se guardan automáticamente
                al finalizar cada sesión de dictado por voz.
              </p>
            </div>
            <ToggleSwitch
              id="auto-save-dictation"
              label="Guardar automáticamente durante el dictado"
              checked={autoSaveDictation}
              onChange={(val) => {
                setAutoSaveDictation(val);
                mark();
              }}
              disabled={!isOwner}
            />
          </div>
        </CardContent>
      </Card>

      {/* ─── Info note ────────────────────────────────────────────────────── */}
      <div className="flex items-start gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/40 px-4 py-3 text-xs text-[hsl(var(--muted-foreground))]">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          La configuración de colores de condiciones y la personalización avanzada del
          odontograma están disponibles en la vista del paciente directamente.
        </span>
      </div>

      <Separator />

      {/* ─── Save button ────────────────────────────────────────────────────── */}
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
