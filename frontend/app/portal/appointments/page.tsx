"use client";

import { useState } from "react";
import {
  usePortalAppointments,
  usePortalCancelAppointment,
} from "@/lib/hooks/use-portal";

export default function PortalAppointments() {
  const [view, setView] = useState<"upcoming" | "past">("upcoming");
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = usePortalAppointments(view);
  const cancelMutation = usePortalCancelAppointment();

  const appointments = data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
          Mis citas
        </h1>
      </div>

      {/* Tab toggle */}
      <div className="flex gap-1 bg-slate-100 dark:bg-zinc-800 rounded-lg p-1">
        {(["upcoming", "past"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setView(tab)}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
              view === tab
                ? "bg-white dark:bg-zinc-900 text-[hsl(var(--foreground))] shadow-sm"
                : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
            }`}
          >
            {tab === "upcoming" ? "Próximas" : "Pasadas"}
          </button>
        ))}
      </div>

      {/* Appointment list */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse"
            />
          ))}
        </div>
      ) : appointments.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">
            {view === "upcoming"
              ? "No tienes citas próximas"
              : "No hay citas pasadas"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {appointments.map((appt) => (
            <div
              key={appt.id}
              className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-[hsl(var(--foreground))] truncate">
                    {appt.doctor_name}
                  </p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
                    {new Date(appt.scheduled_at).toLocaleDateString("es-CO", {
                      weekday: "short",
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    {" — "}
                    {appt.duration_minutes} min
                  </p>
                  {appt.appointment_type && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                      {appt.appointment_type}
                    </p>
                  )}
                  {appt.notes_for_patient && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 italic">
                      {appt.notes_for_patient}
                    </p>
                  )}
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <span
                    className={`px-2 py-0.5 text-xs rounded-full ${
                      appt.status === "confirmed"
                        ? "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400"
                        : appt.status === "pending"
                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400"
                          : appt.status === "cancelled"
                            ? "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-400"
                            : "bg-slate-100 text-slate-700 dark:bg-zinc-800 dark:text-zinc-400"
                    }`}
                  >
                    {appt.status === "confirmed"
                      ? "Confirmada"
                      : appt.status === "pending"
                        ? "Pendiente"
                        : appt.status === "cancelled"
                          ? "Cancelada"
                          : appt.status === "completed"
                            ? "Completada"
                            : appt.status}
                  </span>

                  {view === "upcoming" &&
                    ["confirmed", "pending"].includes(appt.status) && (
                      <button
                        onClick={() =>
                          cancelMutation.mutate({ appointmentId: appt.id })
                        }
                        disabled={cancelMutation.isPending}
                        className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50 transition-colors"
                      >
                        Cancelar
                      </button>
                    )}
                </div>
              </div>
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
