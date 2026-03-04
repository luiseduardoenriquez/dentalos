"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Gift,
  Users,
  Clock,
  CheckCircle,
  TrendingUp,
  AlertCircle,
  ToggleLeft,
  ToggleRight,
  Loader2,
} from "lucide-react";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReferralProgramStats {
  is_active: boolean;
  total_codes_generated: number;
  total_referrals_made: number;
  referrals_pending: number;
  referrals_converted: number;
  rewards_pending: number;
  rewards_applied: number;
  total_discount_given_cents: number;
  reward_type: "discount" | "credit" | "none";
  reward_value_cents: number;
  reward_description: string | null;
}

// ─── Query key ────────────────────────────────────────────────────────────────

const REFERRAL_STATS_KEY = ["referral-program", "stats"] as const;

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse max-w-4xl">
      <div className="h-8 w-56 rounded bg-slate-200 dark:bg-zinc-700" />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="h-24 rounded-xl bg-slate-100 dark:bg-zinc-800"
          />
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * /settings/referral-program
 *
 * Referral program management for clinic_owner.
 * Shows program stats and allows toggling the program on/off.
 */
export default function ReferralProgramPage() {
  const queryClient = useQueryClient();
  const { success, error: toastError } = useToast();

  const { data: stats, isLoading, isError } = useQuery({
    queryKey: REFERRAL_STATS_KEY,
    queryFn: () => apiGet<ReferralProgramStats>("/referral-program/stats"),
    staleTime: 2 * 60_000,
  });

  const { mutate: toggleProgram, isPending: isToggling } = useMutation({
    mutationFn: (activate: boolean) =>
      apiPost<ReferralProgramStats>("/referral-program/toggle", {
        is_active: activate,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(REFERRAL_STATS_KEY, updated);
      success(
        updated.is_active ? "Programa activado" : "Programa desactivado",
        updated.is_active
          ? "El programa de referidos está activo."
          : "Los pacientes ya no podrán usar códigos de referido.",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo cambiar el estado del programa.";
      toastError("Error", message);
    },
  });

  // ─── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) return <PageSkeleton />;

  // ─── Error ──────────────────────────────────────────────────────────────────
  if (isError || !stats) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          Error al cargar estadísticas
        </p>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          No se pudieron obtener las estadísticas del programa de referidos.
        </p>
      </div>
    );
  }

  const totalDiscountFormatted = ((stats.total_discount_given_cents ?? 0) / 100).toLocaleString(
    "es-CO",
    { style: "currency", currency: "COP", minimumFractionDigits: 0 },
  );

  const rewardValueFormatted = ((stats.reward_value_cents ?? 0) / 100).toLocaleString(
    "es-CO",
    { style: "currency", currency: "COP", minimumFractionDigits: 0 },
  );

  // ─── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-8 max-w-4xl">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[hsl(var(--foreground))]">
            Programa de referidos
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Tus pacientes obtienen un código único para invitar amigos. Ambos
            reciben un beneficio al primera cita.
          </p>
        </div>

        {/* Toggle */}
        <button
          onClick={() => toggleProgram(!stats.is_active)}
          disabled={isToggling}
          className={`inline-flex items-center gap-2 self-start rounded-xl px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-60 ${
            stats.is_active
              ? "bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-950/30 dark:text-green-300"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-zinc-800 dark:text-zinc-300"
          }`}
        >
          {isToggling ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : stats.is_active ? (
            <ToggleRight className="h-5 w-5 text-green-600" />
          ) : (
            <ToggleLeft className="h-5 w-5" />
          )}
          {stats.is_active ? "Programa activo" : "Programa inactivo"}
        </button>
      </div>

      {/* Reward config banner */}
      {(stats.reward_value_cents ?? 0) > 0 && (
        <div className="rounded-xl border border-teal-200 bg-teal-50 dark:bg-teal-950/20 dark:border-teal-800 px-5 py-4 flex items-start gap-3">
          <Gift className="h-5 w-5 text-teal-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-teal-800 dark:text-teal-300">
              Beneficio configurado:{" "}
              <span className="font-bold">{rewardValueFormatted}</span>{" "}
              {stats.reward_type === "discount" ? "de descuento" : "de crédito"}{" "}
              por referido
            </p>
            {stats.reward_description && (
              <p className="mt-0.5 text-xs text-teal-700 dark:text-teal-400">
                {stats.reward_description}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Stats grid */}
      <div>
        <h2 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-4">
          Estadísticas del programa
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard
            icon={<Users className="h-5 w-5 text-blue-500" />}
            label="Códigos generados"
            value={stats.total_codes_generated.toLocaleString("es-CO")}
            bg="blue"
          />
          <StatCard
            icon={<TrendingUp className="h-5 w-5 text-teal-500" />}
            label="Referidos realizados"
            value={stats.total_referrals_made.toLocaleString("es-CO")}
            bg="teal"
          />
          <StatCard
            icon={<CheckCircle className="h-5 w-5 text-green-500" />}
            label="Referidos convertidos"
            value={stats.referrals_converted.toLocaleString("es-CO")}
            bg="green"
          />
          <StatCard
            icon={<Clock className="h-5 w-5 text-amber-500" />}
            label="Referidos pendientes"
            value={stats.referrals_pending.toLocaleString("es-CO")}
            bg="amber"
          />
          <StatCard
            icon={<Gift className="h-5 w-5 text-purple-500" />}
            label="Recompensas pendientes"
            value={stats.rewards_pending.toLocaleString("es-CO")}
            bg="purple"
          />
          <StatCard
            icon={<Gift className="h-5 w-5 text-slate-500" />}
            label="Recompensas aplicadas"
            value={stats.rewards_applied.toLocaleString("es-CO")}
            bg="slate"
          />
        </div>
      </div>

      {/* Total discount given */}
      <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-6 py-5">
        <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
          Total de descuentos otorgados
        </p>
        <p className="mt-2 text-3xl font-bold text-[hsl(var(--foreground))]">
          {totalDiscountFormatted}
        </p>
        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
          Suma de todos los beneficios aplicados a pacientes por referidos
        </p>
      </div>

      {/* Conversion rate */}
      {stats.total_referrals_made > 0 && (
        <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-6 py-5">
          <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
            Tasa de conversión
          </p>
          <div className="mt-3 h-3 rounded-full bg-slate-100 dark:bg-zinc-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-teal-500 transition-all duration-500"
              style={{
                width: `${Math.round(
                  (stats.referrals_converted / stats.total_referrals_made) *
                    100,
                )}%`,
              }}
            />
          </div>
          <p className="mt-2 text-sm font-semibold text-[hsl(var(--foreground))]">
            {Math.round(
              (stats.referrals_converted / stats.total_referrals_made) * 100,
            )}
            %{" "}
            <span className="text-xs font-normal text-[hsl(var(--muted-foreground))]">
              ({stats.referrals_converted} de {stats.total_referrals_made})
            </span>
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Stat card ────────────────────────────────────────────────────────────────

type StatBg = "blue" | "teal" | "green" | "amber" | "purple" | "slate";

const BG_CLASSES: Record<StatBg, string> = {
  blue: "bg-blue-50 dark:bg-blue-950/20",
  teal: "bg-teal-50 dark:bg-teal-950/20",
  green: "bg-green-50 dark:bg-green-950/20",
  amber: "bg-amber-50 dark:bg-amber-950/20",
  purple: "bg-purple-50 dark:bg-purple-950/20",
  slate: "bg-slate-50 dark:bg-zinc-900",
};

function StatCard({
  icon,
  label,
  value,
  bg,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  bg: StatBg;
}) {
  return (
    <div
      className={`rounded-xl p-4 border border-[hsl(var(--border))] ${BG_CLASSES[bg]}`}
    >
      <div className="flex items-center gap-2 mb-2">{icon}</div>
      <p className="text-2xl font-bold text-[hsl(var(--foreground))]">
        {value}
      </p>
      <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
        {label}
      </p>
    </div>
  );
}
