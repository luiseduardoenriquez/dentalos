"use client";

import * as React from "react";
import Link from "next/link";
import {
  ChevronLeft,
  CalendarDays,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  UserX,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { AppointmentStatusBadge, AppointmentTypeBadge } from "@/components/agenda/appointment-status-badge";
import { AppointmentDetailModal } from "@/components/agenda/appointment-detail-modal";
import {
  useAppointments,
  useConfirmAppointment,
  useCompleteAppointment,
  useNoShow,
  type Appointment,
} from "@/lib/hooks/use-appointments";
import { cn, formatTime } from "@/lib/utils";
import type { AppointmentStatus } from "@/lib/validations/appointment";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getToday(): { from: string; to: string } {
  const today = new Date().toISOString().slice(0, 10);
  return { from: today, to: today };
}

function isCurrentTimeWithin(
  start_time: string,
  end_time: string,
): boolean {
  const now = new Date();
  return now >= new Date(start_time) && now <= new Date(end_time);
}

function isUpcoming(start_time: string): boolean {
  return new Date(start_time) > new Date();
}

function isPast(end_time: string): boolean {
  return new Date(end_time) < new Date();
}

function formatTimeRange(start: string, end: string): string {
  return `${formatTime(start)} – ${formatTime(end)}`;
}

// ─── Current Time Indicator ───────────────────────────────────────────────────

function CurrentTimeIndicator() {
  const [, force_update] = React.useState(0);

  // Re-render every minute to keep the time line fresh
  React.useEffect(() => {
    const interval = setInterval(() => force_update((n) => n + 1), 60_000);
    return () => clearInterval(interval);
  }, []);

  const now = new Date();
  const time_str = now.toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  return (
    <div className="flex items-center gap-2 py-1">
      <div className="h-3 w-3 rounded-full bg-red-500 shrink-0 animate-pulse" />
      <div className="flex-1 border-t-2 border-red-400 border-dashed" />
      <span className="text-xs font-semibold text-red-500 tabular-nums shrink-0">
        {time_str}
      </span>
    </div>
  );
}

// ─── Appointment Card ─────────────────────────────────────────────────────────

interface AppointmentCardProps {
  appointment: Appointment;
  is_next: boolean;
  on_view: (id: string) => void;
}

function AppointmentCard({ appointment, is_next, on_view }: AppointmentCardProps) {
  const { mutate: confirm, isPending: is_confirming } = useConfirmAppointment();
  const { mutate: complete, isPending: is_completing } = useCompleteAppointment();
  const { mutate: no_show, isPending: is_no_showing } = useNoShow();

  const is_pending_any = is_confirming || is_completing || is_no_showing;

  const status = appointment.status as AppointmentStatus;
  const is_terminal = ["completed", "cancelled", "no_show"].includes(status);
  const is_active = isCurrentTimeWithin(appointment.start_time, appointment.end_time);
  const is_upcoming = isUpcoming(appointment.start_time);
  const is_past = isPast(appointment.end_time);

  return (
    <div
      className={cn(
        "rounded-xl border bg-[hsl(var(--background))] p-4 transition-all",
        is_active && "border-primary-400 shadow-md ring-1 ring-primary-200 dark:ring-primary-800",
        is_next && !is_active && "border-amber-300 dark:border-amber-700",
        is_terminal && "opacity-75",
        !is_active && !is_next && !is_terminal && "border-[hsl(var(--border))]",
      )}
    >
      {/* ─── Header row ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <AppointmentStatusBadge status={status} />
          <AppointmentTypeBadge type={appointment.type} />
          {is_next && !is_active && (
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-amber-100 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700">
              Próxima
            </span>
          )}
          {is_active && (
            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-primary-100 text-primary-700 border border-primary-300 dark:bg-primary-900/30 dark:text-primary-300 dark:border-primary-700">
              <span className="h-1.5 w-1.5 rounded-full bg-primary-600 animate-pulse" />
              En curso
            </span>
          )}
        </div>

        <Button
          variant="outline"
          size="sm"
          className="shrink-0 h-7 px-2 text-xs"
          onClick={() => on_view(appointment.id)}
        >
          Ver detalle
        </Button>
      </div>

      {/* ─── Patient & time ─────────────────────────────────────────── */}
      <div className="flex items-center gap-3 mb-3">
        {/* Avatar */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]">
          <User className="h-5 w-5" />
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-semibold text-foreground truncate">
            {appointment.patient_name ?? "Paciente"}
          </p>
          <div className="flex items-center gap-1.5 mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
            <Clock className="h-3 w-3 shrink-0" />
            <span className="tabular-nums">
              {formatTimeRange(appointment.start_time, appointment.end_time)}
            </span>
            <span>·</span>
            <span>{appointment.duration_minutes} min</span>
          </div>
          {appointment.doctor_name && (
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5 truncate">
              Dr. {appointment.doctor_name}
            </p>
          )}
        </div>
      </div>

      {/* ─── Quick actions ──────────────────────────────────────────── */}
      {!is_terminal && (
        <div className="flex gap-2 pt-2 border-t border-[hsl(var(--border))]">
          {/* Confirm — only for scheduled */}
          {status === "scheduled" && (
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-8 text-xs text-green-700 border-green-300 hover:bg-green-50 dark:text-green-400 dark:border-green-700 dark:hover:bg-green-950/30"
              onClick={() => confirm(appointment.id)}
              disabled={is_pending_any}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
              Confirmar
            </Button>
          )}

          {/* Complete — for confirmed and in_progress */}
          {(status === "confirmed" || status === "in_progress") && (
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-8 text-xs text-green-700 border-green-300 hover:bg-green-50 dark:text-green-400 dark:border-green-700 dark:hover:bg-green-950/30"
              onClick={() => complete({ id: appointment.id })}
              disabled={is_pending_any}
            >
              {is_completing ? (
                <span className="flex items-center gap-1">
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-green-600 border-t-transparent" />
                  Completando...
                </span>
              ) : (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                  Completar
                </>
              )}
            </Button>
          )}

          {/* No-show — for scheduled/confirmed only in the past */}
          {(status === "scheduled" || status === "confirmed") && (is_past || is_active) && (
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-8 text-xs text-amber-700 border-amber-300 hover:bg-amber-50 dark:text-amber-400 dark:border-amber-700 dark:hover:bg-amber-950/30"
              onClick={() => no_show(appointment.id)}
              disabled={is_pending_any}
            >
              {is_no_showing ? (
                <span className="flex items-center gap-1">
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
                  Registrando...
                </span>
              ) : (
                <>
                  <UserX className="h-3.5 w-3.5 mr-1" />
                  No asistió
                </>
              )}
            </Button>
          )}
        </div>
      )}

      {/* Terminal status info */}
      {status === "cancelled" && appointment.cancellation_reason && (
        <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))] italic">
          Motivo: {appointment.cancellation_reason}
        </p>
      )}
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function TodaySkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-[hsl(var(--border))] p-4 space-y-3"
        >
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-24 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-10 rounded-full shrink-0" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-3 w-28" />
            </div>
          </div>
          <div className="flex gap-2 pt-2 border-t border-[hsl(var(--border))]">
            <Skeleton className="h-8 flex-1 rounded-md" />
            <Skeleton className="h-8 flex-1 rounded-md" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Today's appointments timeline (FE-AG-06).
 *
 * A simplified daily view showing:
 * - All appointments for today sorted by start time
 * - Current time indicator (red dashed line)
 * - Next appointment highlighted in amber
 * - Quick action buttons per card (confirm, complete, no-show)
 * - Detail modal on "Ver detalle" click
 */
export default function AgendaTodayPage() {
  const { from, to } = getToday();
  const today_label = new Date().toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const { data, isLoading, isError, refetch } = useAppointments({
    date_from: from,
    date_to: to,
    page_size: 50,
  });

  // ─── Detail modal state ──────────────────────────────────────────────
  const [detail_open, set_detail_open] = React.useState(false);
  const [selected_id, set_selected_id] = React.useState<string | null>(null);

  function handle_view(id: string) {
    set_selected_id(id);
    set_detail_open(true);
  }

  const appointments = data?.items ?? [];

  // Sort by start time
  const sorted = [...appointments].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
  );

  // Find the next upcoming appointment
  const next_id = sorted.find((a) =>
    isUpcoming(a.start_time) &&
    !["completed", "cancelled", "no_show"].includes(a.status),
  )?.id;

  // Summary counts
  const scheduled_count = appointments.filter((a) =>
    ["scheduled", "confirmed"].includes(a.status),
  ).length;
  const completed_count = appointments.filter(
    (a) => a.status === "completed",
  ).length;
  const cancelled_count = appointments.filter(
    (a) => a.status === "cancelled" || a.status === "no_show",
  ).length;

  return (
    <div className="flex flex-col h-full p-6 gap-5">
      {/* ─── Header ───────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" asChild>
          <Link href="/agenda">
            <ChevronLeft className="h-4 w-4 mr-1" />
            Agenda
          </Link>
        </Button>

        <div className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5 text-primary-600" />
          <div>
            <h1 className="text-xl font-bold text-foreground capitalize">
              Hoy — {today_label}
            </h1>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {appointments.length} cita{appointments.length !== 1 ? "s" : ""} programada
              {appointments.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
      </div>

      {/* ─── Stats strip ──────────────────────────────────────────────── */}
      {appointments.length > 0 && (
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
            <Clock className="h-3.5 w-3.5" />
            <span className="font-medium">{scheduled_count}</span>
            <span className="text-[hsl(var(--muted-foreground))]">pendiente{scheduled_count !== 1 ? "s" : ""}</span>
          </div>
          <div className="flex items-center gap-1.5 text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span className="font-medium">{completed_count}</span>
            <span className="text-[hsl(var(--muted-foreground))]">completada{completed_count !== 1 ? "s" : ""}</span>
          </div>
          {cancelled_count > 0 && (
            <div className="flex items-center gap-1.5 text-red-600 dark:text-red-400">
              <XCircle className="h-3.5 w-3.5" />
              <span className="font-medium">{cancelled_count}</span>
              <span className="text-[hsl(var(--muted-foreground))]">cancelada{cancelled_count !== 1 ? "s" : ""}</span>
            </div>
          )}
        </div>
      )}

      {/* ─── Content ──────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {/* Loading */}
        {isLoading && <TodaySkeleton />}

        {/* Error */}
        {isError && !isLoading && (
          <EmptyState
            icon={AlertCircle}
            title="Error al cargar las citas"
            description="No se pudieron obtener las citas de hoy. Inténtalo de nuevo."
            action={{ label: "Reintentar", onClick: () => refetch() }}
          />
        )}

        {/* Empty */}
        {!isLoading && !isError && sorted.length === 0 && (
          <EmptyState
            icon={CalendarDays}
            title="No hay citas para hoy"
            description="No hay citas programadas para hoy. Agenda nuevas citas desde la vista de calendario."
            action={{ label: "Ver agenda", href: "/agenda" }}
          />
        )}

        {/* Appointment list */}
        {!isLoading && !isError && sorted.length > 0 && (
          <div className="space-y-3">
            {sorted.map((appt, idx) => {
              const prev = sorted[idx - 1];
              const is_next = appt.id === next_id;

              // Insert current-time indicator before the first upcoming appointment
              const show_time_indicator =
                is_next &&
                idx > 0 &&
                prev &&
                new Date(prev.end_time) < new Date();

              return (
                <React.Fragment key={appt.id}>
                  {show_time_indicator && <CurrentTimeIndicator />}

                  {/* Insert indicator at top if all appointments are upcoming */}
                  {is_next && idx === 0 && <CurrentTimeIndicator />}

                  <AppointmentCard
                    appointment={appt}
                    is_next={is_next}
                    on_view={handle_view}
                  />
                </React.Fragment>
              );
            })}

            {/* Indicator at the end if all are past */}
            {sorted.every((a) => isPast(a.end_time)) && (
              <CurrentTimeIndicator />
            )}
          </div>
        )}
      </div>

      {/* ─── Detail Modal ─────────────────────────────────────────────── */}
      <AppointmentDetailModal
        appointmentId={selected_id}
        open={detail_open}
        onOpenChange={(v) => {
          if (!v) {
            set_detail_open(false);
            set_selected_id(null);
          }
        }}
      />
    </div>
  );
}
