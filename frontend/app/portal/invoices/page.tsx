"use client";

import { useState } from "react";
import Link from "next/link";
import { usePortalInvoices, usePortalMe } from "@/lib/hooks/use-portal";

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    { label: string; className: string }
  > = {
    paid: {
      label: "Pagada",
      className:
        "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400",
    },
    pending: {
      label: "Pendiente",
      className:
        "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400",
    },
    partial: {
      label: "Parcial",
      className:
        "bg-orange-100 text-orange-700 dark:bg-orange-950/30 dark:text-orange-400",
    },
    cancelled: {
      label: "Anulada",
      className:
        "bg-slate-100 text-slate-600 dark:bg-zinc-800 dark:text-zinc-400",
    },
  };

  const c = config[status] ?? {
    label: status,
    className: "bg-slate-100 text-slate-600 dark:bg-zinc-800 dark:text-zinc-400",
  };

  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${c.className}`}>
      {c.label}
    </span>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalInvoices() {
  const { data: profile } = usePortalMe();
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = usePortalInvoices();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const invoices = data?.pages.flatMap((p) => p.data) ?? [];
  const outstandingBalance = profile?.outstanding_balance ?? 0;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
        Pagos y facturas
      </h1>

      {/* Outstanding balance summary */}
      <div
        className={`rounded-xl border p-5 ${
          outstandingBalance > 0
            ? "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-800"
            : "bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-800"
        }`}
      >
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Saldo pendiente
        </p>
        <p
          className={`text-3xl font-bold mt-1 ${
            outstandingBalance > 0
              ? "text-yellow-700 dark:text-yellow-400"
              : "text-green-700 dark:text-green-400"
          }`}
        >
          ${(outstandingBalance / 100).toLocaleString("es-CO")}
        </p>
        {outstandingBalance === 0 && (
          <p className="text-sm text-green-600 dark:text-green-400 mt-1">
            Estás al día con tus pagos
          </p>
        )}
      </div>

      {/* Invoice list */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse"
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
      ) : invoices.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">
            No tienes facturas
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {invoices.map((inv) => {
            const isExpanded = expandedId === inv.id;

            return (
              <div
                key={inv.id}
                className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] overflow-hidden"
              >
                {/* Summary row */}
                <button
                  onClick={() =>
                    setExpandedId(isExpanded ? null : inv.id)
                  }
                  className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-sm text-[hsl(var(--foreground))]">
                      {inv.invoice_number
                        ? `Factura ${inv.invoice_number}`
                        : "Factura"}
                    </p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                      {new Date(inv.date).toLocaleDateString("es-CO", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <StatusBadge status={inv.status} />
                    <span className="font-semibold text-sm text-[hsl(var(--foreground))]">
                      ${(inv.total / 100).toLocaleString("es-CO")}
                    </span>
                    <svg
                      className={`w-4 h-4 text-[hsl(var(--muted-foreground))] transition-transform ${
                        isExpanded ? "rotate-90" : ""
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </button>

                {/* Line items (expanded) */}
                {isExpanded && (
                  <div className="border-t border-[hsl(var(--border))] px-4 py-3 space-y-2">
                    {inv.line_items.length === 0 ? (
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Sin detalle de líneas
                      </p>
                    ) : (
                      <>
                        {inv.line_items.map((li, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between text-sm"
                          >
                            <span className="text-[hsl(var(--muted-foreground))] min-w-0 truncate pr-4">
                              {li.description}
                              {li.quantity > 1 && (
                                <span className="ml-1 text-xs">
                                  x{li.quantity}
                                </span>
                              )}
                            </span>
                            <span className="text-[hsl(var(--foreground))] shrink-0">
                              ${(li.total / 100).toLocaleString("es-CO")}
                            </span>
                          </div>
                        ))}
                        {/* Paid / Total footer */}
                        <div className="flex justify-between text-sm font-semibold pt-2 border-t border-[hsl(var(--border))]">
                          <span className="text-[hsl(var(--muted-foreground))]">
                            Pagado / Total
                          </span>
                          <span className="text-[hsl(var(--foreground))]">
                            ${(inv.paid / 100).toLocaleString("es-CO")} /{" "}
                            ${(inv.total / 100).toLocaleString("es-CO")}
                          </span>
                        </div>
                        {inv.balance > 0 && (
                          <div className="flex justify-between text-sm text-yellow-600 dark:text-yellow-400">
                            <span>Por pagar</span>
                            <span>
                              ${(inv.balance / 100).toLocaleString("es-CO")}
                            </span>
                          </div>
                        )}
                        {inv.balance > 0 && inv.status !== "cancelled" && (
                          <div className="pt-2">
                            <Link
                              href={`/portal/invoices/${inv.id}/pay`}
                              className="inline-flex items-center justify-center w-full py-2 px-4 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
                            >
                              Pagar ahora
                            </Link>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}

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
