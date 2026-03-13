"use client";

import { useState } from "react";
import {
  usePortalAppointments,
  usePortalCancelAppointment,
  usePortalRescheduleAppointment,
} from "@/lib/hooks/use-portal";
import { toast } from "sonner";

export default function PortalAppointments() {
  const [view, setView] = useState<"upcoming" | "past">("upcoming");
  const [rescheduleId, setRescheduleId] = useState<string | null>(null);
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = usePortalAppointments(view);
  const cancelMutation = usePortalCancelAppointment();
  const rescheduleMutation = usePortalRescheduleAppointment();

  function handleReschedule(appointmentId: string) {
    if (!newDate || !newTime) {
      toast.error("Selecciona fecha y hora para reagendar.");
      return;
    }
    rescheduleMutation.mutate(
      { appointmentId, new_date: newDate, new_time: newTime },
      {
        onSuccess: () => {
          toast.success("Cita reagendada exitosamente.");
          setRescheduleId(null);
          setNewDate("");
          setNewTime("");
        },
        onError: (err) => {
          toast.error(
            err instanceof Error ? err.message : "Error al reagendar la cita.",
          );
        },
      },
    );
  }

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
                    ["confirmed", "pending", "scheduled"].includes(appt.status) && (
                      <div className="flex gap-2">
                        <button
                          onClick={() =>
                            setRescheduleId(
                              rescheduleId === appt.id ? null : appt.id,
                            )
                          }
                          className="text-xs text-primary-600 hover:text-primary-700 transition-colors"
                        >
                          Reagendar
                        </button>
                        <button
                          onClick={() =>
                            cancelMutation.mutate({ appointmentId: appt.id })
                          }
                          disabled={cancelMutation.isPending}
                          className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50 transition-colors"
                        >
                          Cancelar
                        </button>
                      </div>
                    )}
                </div>
              </div>

              {/* Reschedule form */}
              {rescheduleId === appt.id && (
                <div className="border-t border-[hsl(var(--border))] px-4 py-3 flex flex-wrap items-end gap-3">
                  <div>
                    <label className="text-xs text-[hsl(var(--muted-foreground))] block mb-1">
                      Nueva fecha
                    </label>
                    <input
                      type="date"
                      value={newDate}
                      onChange={(e) => setNewDate(e.target.value)}
                      min={new Date().toISOString().split("T")[0]}
                      className="rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-sm bg-white dark:bg-zinc-900"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-[hsl(var(--muted-foreground))] block mb-1">
                      Nueva hora
                    </label>
                    <input
                      type="time"
                      value={newTime}
                      onChange={(e) => setNewTime(e.target.value)}
                      className="rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-sm bg-white dark:bg-zinc-900"
                    />
                  </div>
                  <button
                    onClick={() => handleReschedule(appt.id)}
                    disabled={rescheduleMutation.isPending}
                    className="px-4 py-1.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
                  >
                    {rescheduleMutation.isPending
                      ? "Reagendando..."
                      : "Confirmar"}
                  </button>
                  <button
                    onClick={() => {
                      setRescheduleId(null);
                      setNewDate("");
                      setNewTime("");
                    }}
                    className="px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] text-sm text-[hsl(var(--muted-foreground))] hover:bg-slate-50 dark:hover:bg-zinc-800 transition-colors"
                  >
                    Cancelar
                  </button>
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
