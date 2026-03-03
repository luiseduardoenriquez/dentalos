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
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, AlertCircle, Star, ToggleLeft, ToggleRight, Loader2 } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface LoyaltySettings {
  is_enabled: boolean;
  points_per_appointment: number;
  points_per_referral: number;
  points_per_on_time_payment: number;
  points_to_currency_ratio: number;
  expiry_months: number;
}

// ─── Default values ───────────────────────────────────────────────────────────

const DEFAULT_SETTINGS: LoyaltySettings = {
  is_enabled: false,
  points_per_appointment: 100,
  points_per_referral: 500,
  points_per_on_time_payment: 50,
  points_to_currency_ratio: 10,
  expiry_months: 12,
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LoyaltySettingsPage() {
  const queryClient = useQueryClient();
  const [saved, setSaved] = React.useState(false);
  const [form, setForm] = React.useState<LoyaltySettings>(DEFAULT_SETTINGS);

  const { data: settingsData, isLoading, isError } = useQuery({
    queryKey: ["settings", "loyalty"],
    queryFn: () => apiGet<LoyaltySettings>("/settings/loyalty"),
    staleTime: 2 * 60_000,
  });

  // Populate form when data loads
  React.useEffect(() => {
    if (settingsData) setForm(settingsData);
  }, [settingsData]);

  const { mutate: saveSettings, isPending: isSaving } = useMutation({
    mutationFn: (payload: LoyaltySettings) =>
      apiPut<LoyaltySettings>("/settings/loyalty", payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["settings", "loyalty"], updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    saveSettings(form);
  }

  function updateNumber(field: keyof LoyaltySettings, value: string) {
    const parsed = parseFloat(value) || 0;
    setForm((prev) => ({ ...prev, [field]: parsed }));
  }

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-2xl animate-pulse">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm text-red-600 dark:text-red-400">
          Error al cargar la configuración de fidelización.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Programa de fidelización
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Configura cómo los pacientes acumulan y canjean puntos de lealtad.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* ─── Enable/Disable Toggle ───────────────────────────────────── */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Programa de fidelización
                </p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                  {form.is_enabled
                    ? "Activo — los pacientes acumulan puntos."
                    : "Inactivo — los pacientes no acumulan puntos."}
                </p>
              </div>
              <button
                type="button"
                onClick={() =>
                  setForm((prev) => ({ ...prev, is_enabled: !prev.is_enabled }))
                }
                className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors ${
                  form.is_enabled
                    ? "bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-950/30 dark:text-green-300"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-zinc-800 dark:text-zinc-300"
                }`}
              >
                {form.is_enabled ? (
                  <ToggleRight className="h-5 w-5 text-green-600" />
                ) : (
                  <ToggleLeft className="h-5 w-5" />
                )}
                {form.is_enabled ? "Activado" : "Desactivado"}
              </button>
            </div>
          </CardContent>
        </Card>

        {/* ─── Points Configuration ────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Star className="h-4 w-4 text-yellow-500" />
              Acumulación de puntos
            </CardTitle>
            <CardDescription>
              Define cuántos puntos recibe el paciente por cada acción.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="points-appointment">Por cita completada</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="points-appointment"
                    type="number"
                    min={0}
                    className="w-24"
                    value={form.points_per_appointment}
                    onChange={(e) => updateNumber("points_per_appointment", e.target.value)}
                    disabled={!form.is_enabled}
                  />
                  <span className="text-sm text-[hsl(var(--muted-foreground))]">pts</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="points-referral">Por referido convertido</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="points-referral"
                    type="number"
                    min={0}
                    className="w-24"
                    value={form.points_per_referral}
                    onChange={(e) => updateNumber("points_per_referral", e.target.value)}
                    disabled={!form.is_enabled}
                  />
                  <span className="text-sm text-[hsl(var(--muted-foreground))]">pts</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="points-payment">Por pago puntual</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="points-payment"
                    type="number"
                    min={0}
                    className="w-24"
                    value={form.points_per_on_time_payment}
                    onChange={(e) =>
                      updateNumber("points_per_on_time_payment", e.target.value)
                    }
                    disabled={!form.is_enabled}
                  />
                  <span className="text-sm text-[hsl(var(--muted-foreground))]">pts</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ─── Redemption Configuration ────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Canje de puntos</CardTitle>
            <CardDescription>
              Configura el valor de los puntos al momento del canje.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="ratio">Ratio de conversión</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="ratio"
                  type="number"
                  min={1}
                  className="w-24"
                  value={form.points_to_currency_ratio}
                  onChange={(e) => updateNumber("points_to_currency_ratio", e.target.value)}
                  disabled={!form.is_enabled}
                />
                <span className="text-sm text-[hsl(var(--muted-foreground))]">
                  puntos = $1 COP de descuento
                </span>
              </div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Ej: con ratio 10, el paciente necesita 1.000 pts para obtener $100 de descuento.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="expiry">Meses hasta expiración de puntos</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="expiry"
                  type="number"
                  min={1}
                  max={60}
                  className="w-24"
                  value={form.expiry_months}
                  onChange={(e) => updateNumber("expiry_months", e.target.value)}
                  disabled={!form.is_enabled}
                />
                <span className="text-sm text-[hsl(var(--muted-foreground))]">meses</span>
              </div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Los puntos no canjeados expirarán después de este período desde su acumulación.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* ─── Actions ─────────────────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Guardando...
              </>
            ) : (
              "Guardar configuración"
            )}
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
