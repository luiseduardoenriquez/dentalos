"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Gift, ChevronLeft, AlertCircle } from "lucide-react";
import Link from "next/link";
import { portalApiGet } from "@/lib/portal-api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReferralReward {
  id: string;
  created_at: string;
  reward_type: "descuento" | "credito";
  amount_cents: number;
  status: "pendiente" | "aplicado" | "expirado";
  applied_at: string | null;
  expires_at: string | null;
  description: string | null;
}

interface ReferralRewardsResponse {
  items: ReferralReward[];
  total: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string }
> = {
  pendiente: {
    label: "Pendiente",
    color:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400",
  },
  aplicado: {
    label: "Aplicado",
    color:
      "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400",
  },
  expirado: {
    label: "Expirado",
    color:
      "bg-slate-100 text-slate-600 dark:bg-zinc-800 dark:text-zinc-400",
  },
};

const REWARD_TYPE_LABELS: Record<string, string> = {
  descuento: "Descuento",
  credito: "Crédito en cuenta",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatCurrency(cents: number) {
  return (cents / 100).toLocaleString("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
  });
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function RewardsSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-20 rounded-xl bg-slate-100 dark:bg-zinc-800"
        />
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * /portal/referral/rewards
 *
 * Patient portal rewards list page.
 * Shows all referral rewards (pending, applied, expired).
 */
export default function PortalReferralRewardsPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["portal", "referral", "rewards"],
    queryFn: () =>
      portalApiGet<ReferralRewardsResponse>("/portal/referral/rewards"),
    staleTime: 60_000,
  });

  const rewards = data?.items ?? [];

  const pendingCount = rewards.filter((r) => r.status === "pendiente").length;
  const totalPendingCents = rewards
    .filter((r) => r.status === "pendiente")
    .reduce((sum, r) => sum + r.amount_cents, 0);

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Back link */}
      <Link
        href="/portal/referral"
        className="inline-flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors"
      >
        <ChevronLeft className="h-4 w-4" />
        Volver a referidos
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))] flex items-center gap-2">
          <Gift className="h-5 w-5 text-teal-600" />
          Mis recompensas
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Historial de beneficios ganados por tus referidos.
        </p>
      </div>

      {/* Pending balance summary */}
      {!isLoading && pendingCount > 0 && (
        <div className="rounded-xl border border-teal-200 bg-teal-50 dark:bg-teal-950/20 dark:border-teal-800 px-5 py-4">
          <p className="text-xs text-teal-700 dark:text-teal-400 font-medium uppercase tracking-wider">
            Recompensas disponibles
          </p>
          <p className="mt-1 text-2xl font-bold text-teal-800 dark:text-teal-300">
            {formatCurrency(totalPendingCents)}
          </p>
          <p className="mt-0.5 text-xs text-teal-700 dark:text-teal-400">
            {pendingCount} recompensa{pendingCount > 1 ? "s" : ""} pendiente
            {pendingCount > 1 ? "s" : ""} de aplicar
          </p>
        </div>
      )}

      {/* Rewards list */}
      {isLoading ? (
        <RewardsSkeleton />
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
          <AlertCircle className="h-6 w-6 text-red-500" />
          <p className="text-sm text-red-600 dark:text-red-400 font-medium">
            Error al cargar las recompensas
          </p>
          <button
            onClick={() => refetch()}
            className="text-sm text-teal-600 hover:underline"
          >
            Reintentar
          </button>
        </div>
      ) : rewards.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[hsl(var(--border))] py-12 text-center">
          <Gift className="h-8 w-8 text-[hsl(var(--muted-foreground))] mx-auto mb-3" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Aún no tienes recompensas.
          </p>
          <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
            Comparte tu código de referido para empezar a ganar beneficios.
          </p>
          <Link
            href="/portal/referral"
            className="mt-4 inline-block text-sm text-teal-600 hover:underline font-medium"
          >
            Ver mi código
          </Link>
        </div>
      ) : (
        <>
          {/* Table header */}
          <div className="hidden md:grid grid-cols-[1fr_auto_auto_auto] gap-4 px-4 py-2 text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
            <span>Tipo</span>
            <span className="text-right">Monto</span>
            <span>Estado</span>
            <span>Fecha</span>
          </div>

          {/* Rows */}
          <div className="space-y-2">
            {rewards.map((reward) => {
              const statusConfig =
                STATUS_CONFIG[reward.status] ?? STATUS_CONFIG.pendiente;
              return (
                <div
                  key={reward.id}
                  className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-4 py-3"
                >
                  {/* Mobile layout */}
                  <div className="flex items-start justify-between gap-3 md:hidden">
                    <div>
                      <p className="text-sm font-medium text-[hsl(var(--foreground))]">
                        {REWARD_TYPE_LABELS[reward.reward_type] ??
                          reward.reward_type}
                      </p>
                      {reward.description && (
                        <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
                          {reward.description}
                        </p>
                      )}
                      <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                        {formatDate(reward.created_at)}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1.5">
                      <p className="text-sm font-bold text-[hsl(var(--foreground))]">
                        {formatCurrency(reward.amount_cents)}
                      </p>
                      <span
                        className={`px-2 py-0.5 text-xs rounded-full font-medium ${statusConfig.color}`}
                      >
                        {statusConfig.label}
                      </span>
                    </div>
                  </div>

                  {/* Desktop layout */}
                  <div className="hidden md:grid grid-cols-[1fr_auto_auto_auto] gap-4 items-center">
                    <div>
                      <p className="text-sm font-medium text-[hsl(var(--foreground))]">
                        {REWARD_TYPE_LABELS[reward.reward_type] ??
                          reward.reward_type}
                      </p>
                      {reward.description && (
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">
                          {reward.description}
                        </p>
                      )}
                    </div>
                    <p className="text-sm font-bold text-[hsl(var(--foreground))] text-right">
                      {formatCurrency(reward.amount_cents)}
                    </p>
                    <span
                      className={`px-2 py-0.5 text-xs rounded-full font-medium w-fit ${statusConfig.color}`}
                    >
                      {statusConfig.label}
                    </span>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                      {formatDate(reward.created_at)}
                    </p>
                  </div>

                  {/* Applied / Expires sub-row */}
                  {(reward.applied_at || reward.expires_at) && (
                    <p className="mt-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                      {reward.applied_at
                        ? `Aplicado: ${formatDate(reward.applied_at)}`
                        : reward.expires_at
                          ? `Expira: ${formatDate(reward.expires_at)}`
                          : null}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
