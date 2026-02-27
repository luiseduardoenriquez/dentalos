"use client";

import { useState } from "react";
import {
  usePortalTreatmentPlans,
  usePortalApprovePlan,
} from "@/lib/hooks/use-portal";
import { SignaturePad } from "@/components/signature-pad";

export default function PortalTreatmentPlans() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = usePortalTreatmentPlans();
  const approveMutation = usePortalApprovePlan();

  // Track which plan is being confirmed before approval
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  // Track which plan has the signature modal open
  const [signingId, setSigningId] = useState<string | null>(null);

  const plans = data?.pages.flatMap((p) => p.data) ?? [];

  async function handleApprove(planId: string, signatureBase64: string) {
    await approveMutation.mutateAsync({
      planId,
      signature_data: signatureBase64,
      agreed_terms: true,
    });
    setSigningId(null);
    setConfirmingId(null);
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
        Planes de tratamiento
      </h1>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-40 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse"
            />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">
            Error al cargar los datos
          </p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      ) : plans.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">
            No tienes planes de tratamiento
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5"
            >
              {/* Header row */}
              <div className="flex items-start justify-between mb-3 gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-[hsl(var(--foreground))] truncate">
                    {plan.name}
                  </h3>
                  <span
                    className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full ${
                      plan.status === "approved"
                        ? "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400"
                        : plan.status === "pending_approval"
                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400"
                          : plan.status === "in_progress"
                            ? "bg-primary-100 text-primary-700 dark:bg-primary-950/30 dark:text-primary-400"
                            : "bg-slate-100 text-slate-700 dark:bg-zinc-800 dark:text-zinc-400"
                    }`}
                  >
                    {plan.status === "approved"
                      ? "Aprobado"
                      : plan.status === "pending_approval"
                        ? "Pendiente de aprobación"
                        : plan.status === "in_progress"
                          ? "En progreso"
                          : plan.status === "completed"
                            ? "Completado"
                            : plan.status}
                  </span>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    Total
                  </p>
                  <p className="font-bold text-[hsl(var(--foreground))]">
                    ${(plan.total / 100).toLocaleString("es-CO")}
                  </p>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mb-4">
                <div className="flex justify-between text-xs text-[hsl(var(--muted-foreground))] mb-1">
                  <span>Progreso</span>
                  <span>{plan.progress_pct}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 dark:bg-zinc-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary-600 transition-all duration-500"
                    style={{ width: `${plan.progress_pct}%` }}
                  />
                </div>
              </div>

              {/* Procedures list */}
              <div className="space-y-1.5">
                {plan.procedures.slice(0, 5).map((proc) => (
                  <div
                    key={proc.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div
                        className={`w-2 h-2 rounded-full shrink-0 ${
                          proc.status === "completed"
                            ? "bg-green-500"
                            : proc.status === "in_progress"
                              ? "bg-primary-500"
                              : "bg-slate-300 dark:bg-zinc-600"
                        }`}
                      />
                      <span className="text-[hsl(var(--foreground))] truncate">
                        {proc.name}
                      </span>
                      {proc.tooth_number && (
                        <span className="text-xs text-[hsl(var(--muted-foreground))] shrink-0">
                          D{proc.tooth_number}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        ${(proc.cost / 100).toLocaleString("es-CO")}
                      </span>
                      <span
                        className={`text-xs ${
                          proc.status === "completed"
                            ? "text-green-600 dark:text-green-400"
                            : proc.status === "in_progress"
                              ? "text-primary-600 dark:text-primary-400"
                              : "text-[hsl(var(--muted-foreground))]"
                        }`}
                      >
                        {proc.status === "completed"
                          ? "Completado"
                          : proc.status === "in_progress"
                            ? "En progreso"
                            : "Pendiente"}
                      </span>
                    </div>
                  </div>
                ))}
                {plan.procedures.length > 5 && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))] pt-1">
                    +{plan.procedures.length - 5} procedimientos más
                  </p>
                )}
              </div>

              {/* Paid / Total summary */}
              {plan.paid > 0 && (
                <div className="mt-3 pt-3 border-t border-[hsl(var(--border))] flex justify-between text-xs text-[hsl(var(--muted-foreground))]">
                  <span>Pagado</span>
                  <span>
                    ${(plan.paid / 100).toLocaleString("es-CO")} /{" "}
                    ${(plan.total / 100).toLocaleString("es-CO")}
                  </span>
                </div>
              )}

              {/* Approve button for pending plans */}
              {plan.status === "pending_approval" && (
                <div className="mt-4">
                  {signingId === plan.id ? (
                    <div className="space-y-3">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Al firmar este plan aceptas los procedimientos y costos
                        indicados. Tu firma digital tiene validez legal (Ley 527/1999).
                      </p>
                      <SignaturePad
                        disabled={approveMutation.isPending}
                        onSignature={(base64) => handleApprove(plan.id, base64)}
                        onClear={() => {}}
                      />
                      <button
                        onClick={() => {
                          setSigningId(null);
                          setConfirmingId(null);
                        }}
                        disabled={approveMutation.isPending}
                        className="w-full px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-sm text-[hsl(var(--muted-foreground))] hover:bg-slate-50 dark:hover:bg-zinc-800 transition-colors"
                      >
                        Cancelar
                      </button>
                    </div>
                  ) : confirmingId === plan.id ? (
                    <div className="space-y-2">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Al aprobar este plan aceptas los procedimientos y costos
                        indicados. Se requiere tu firma digital.
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSigningId(plan.id)}
                          className="flex-1 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
                        >
                          Firmar y aprobar
                        </button>
                        <button
                          onClick={() => setConfirmingId(null)}
                          className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-sm text-[hsl(var(--muted-foreground))] hover:bg-slate-50 dark:hover:bg-zinc-800 transition-colors"
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmingId(plan.id)}
                      className="w-full py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
                    >
                      Aprobar plan
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}

          {hasNextPage && (
            <button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="w-full py-2 text-sm text-primary-600 hover:text-primary-700 font-medium disabled:opacity-50 transition-colors"
            >
              {isFetchingNextPage ? "Cargando..." : "Ver más"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
