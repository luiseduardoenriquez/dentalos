"use client";

import { useState } from "react";
import {
  usePortalMembership,
  usePortalRequestMembershipCancel,
} from "@/lib/hooks/use-portal";

export default function PortalMembership() {
  const { data, isLoading, isError, error, refetch } = usePortalMembership();
  const cancelMutation = usePortalRequestMembershipCancel();
  const [showCancel, setShowCancel] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  async function handleCancelRequest() {
    await cancelMutation.mutateAsync({ reason: cancelReason || undefined });
    setShowCancel(false);
    setCancelReason("");
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Mi plan</h1>

      {isLoading ? (
        <div className="h-48 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">Error al cargar los datos</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button onClick={() => refetch()} className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
            Reintentar
          </button>
        </div>
      ) : !data?.has_membership ? (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-8 text-center">
          <p className="text-[hsl(var(--muted-foreground))]">No tienes una membresía activa</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-2">Consulta con tu clínica para conocer los planes disponibles.</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-[hsl(var(--foreground))]">
                {data.subscription?.plan_name || "Membresía activa"}
              </h2>
              <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400">
                {data.subscription?.status === "active" ? "Activa" : data.subscription?.status}
              </span>
            </div>
          </div>

          {data.subscription?.benefits && data.subscription.benefits.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-[hsl(var(--muted-foreground))] mb-2">Beneficios</h3>
              <ul className="space-y-1">
                {data.subscription.benefits.map((benefit, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-[hsl(var(--foreground))]">
                    <span className="text-green-500">✓</span>
                    {benefit}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.subscription?.billing_date && (
            <div className="pt-3 border-t border-[hsl(var(--border))]">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Próxima fecha de cobro:{" "}
                <span className="font-medium text-[hsl(var(--foreground))]">
                  {new Date(data.subscription.billing_date).toLocaleDateString("es-CO", { day: "numeric", month: "long", year: "numeric" })}
                </span>
              </p>
            </div>
          )}

          {!showCancel ? (
            <button
              onClick={() => setShowCancel(true)}
              className="text-sm text-red-500 hover:text-red-700 font-medium"
            >
              Solicitar cancelación
            </button>
          ) : (
            <div className="space-y-3 pt-3 border-t border-[hsl(var(--border))]">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Tu solicitud será revisada por el equipo de la clínica.
              </p>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Motivo de cancelación (opcional)"
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm resize-none"
                rows={3}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleCancelRequest}
                  disabled={cancelMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {cancelMutation.isPending ? "Enviando..." : "Confirmar solicitud"}
                </button>
                <button
                  onClick={() => setShowCancel(false)}
                  className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-sm text-[hsl(var(--muted-foreground))] hover:bg-slate-50 dark:hover:bg-zinc-800 transition-colors"
                >
                  Cancelar
                </button>
              </div>
              {cancelMutation.isSuccess && (
                <p className="text-sm text-green-600">Solicitud enviada exitosamente.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
