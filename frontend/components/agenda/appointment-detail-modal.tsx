"use client";

import * as React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Calendar,
  Clock,
  User,
  Stethoscope,
  X,
  Check,
  AlertTriangle,
  Ban,
  UserX,
  Play,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useAppointment,
  useCancelAppointment,
  useConfirmAppointment,
  useCompleteAppointment,
  useNoShow,
  useStartAppointment,
  type Appointment,
} from "@/lib/hooks/use-appointments";
import {
  AppointmentStatusBadge,
  AppointmentTypeBadge,
} from "./appointment-status-badge";
import {
  appointmentCompleteSchema,
  type AppointmentCompleteForm,
  CANCELLATION_REASONS,
  CANCELLATION_REASON_LABELS,
  type AppointmentStatus,
} from "@/lib/validations/appointment";
import { z } from "zod";

// ─── Local cancel schema ──────────────────────────────────────────────────────
// Aligns with the existing useCancelAppointment hook interface:
// mutationFn: ({ id, reason, cancelled_by_patient })

const cancelFormSchema = z.object({
  reason: z
    .string()
    .min(1, "Selecciona el motivo de cancelación"),
  cancelled_by_patient: z.boolean().default(false),
});

type CancelFormValues = z.infer<typeof cancelFormSchema>;

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AppointmentDetailModalProps {
  appointmentId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

/** Statuses where the appointment is fully terminal — no further actions allowed */
const TERMINAL_STATUSES: AppointmentStatus[] = ["completed", "cancelled", "no_show"];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Formats the appointment datetime as the canonical DentalOS display format:
 * "Lunes 25 de marzo, 2026 · 10:00 - 10:30"
 */
function format_appointment_range(
  scheduledAt: string,
  durationMinutes: number,
): string {
  const start = new Date(scheduledAt);
  if (isNaN(start.getTime())) return scheduledAt;

  const end = new Date(start.getTime() + durationMinutes * 60_000);

  const date_str = start.toLocaleDateString("es-419", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const start_time = start.toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  const end_time = end.toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  // Capitalize first letter (weekday)
  const capitalized =
    date_str.charAt(0).toUpperCase() + date_str.slice(1);

  return `${capitalized} · ${start_time} - ${end_time}`;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Skeleton placeholder shown while appointment data loads */
function AppointmentDetailSkeleton() {
  return (
    <div className="space-y-5 px-6 py-5">
      {/* Status badges */}
      <div className="flex gap-2">
        <Skeleton className="h-6 w-24 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>

      {/* Patient card */}
      <div className="rounded-xl border border-[hsl(var(--border))] p-4 space-y-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-12 w-12 rounded-full shrink-0" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-3 w-48" />
          </div>
        </div>
      </div>

      {/* Meta block */}
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-40" />
          </div>
        ))}
      </div>

      <Separator />

      {/* Action buttons */}
      <Skeleton className="h-11 w-full rounded-lg" />
      <div className="flex gap-2">
        <Skeleton className="h-9 w-full rounded-md" />
        <Skeleton className="h-9 w-full rounded-md" />
      </div>
    </div>
  );
}

// ─── Cancel form ──────────────────────────────────────────────────────────────

interface CancelFormProps {
  appointmentId: string;
  onCancel: () => void;
}

function CancelForm({ appointmentId, onCancel }: CancelFormProps) {
  const { mutate: cancel, isPending } = useCancelAppointment();

  const {
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<CancelFormValues>({
    resolver: zodResolver(cancelFormSchema),
    defaultValues: { cancelled_by_patient: false },
  });

  function on_submit(values: CancelFormValues) {
    cancel(
      {
        id: appointmentId,
        reason: values.reason,
        cancelled_by_patient: values.cancelled_by_patient,
      },
      { onSuccess: onCancel },
    );
  }

  return (
    <form onSubmit={handleSubmit(on_submit)} className="space-y-4 pt-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-destructive-700 dark:text-destructive-400">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        Cancelar cita
      </div>

      {/* Reason select */}
      <div className="space-y-1.5">
        <Label htmlFor="cancel_reason_select" className="text-sm font-medium">
          Motivo
          <span className="text-destructive-600 dark:text-destructive-400"> *</span>
        </Label>
        <Controller
          name="reason"
          control={control}
          render={({ field }) => (
            <Select value={field.value ?? ""} onValueChange={field.onChange}>
              <SelectTrigger
                id="cancel_reason_select"
                aria-label="Motivo de cancelación"
                aria-invalid={Boolean(errors.reason)}
              >
                <SelectValue placeholder="Selecciona el motivo..." />
              </SelectTrigger>
              <SelectContent>
                {CANCELLATION_REASONS.map((r) => (
                  <SelectItem key={r} value={r}>
                    {CANCELLATION_REASON_LABELS[r]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.reason && (
          <p className="text-xs text-destructive-600 dark:text-destructive-400">
            {errors.reason.message}
          </p>
        )}
      </div>

      {/* Cancelled by patient toggle */}
      <div className="flex items-center gap-2.5">
        <Controller
          name="cancelled_by_patient"
          control={control}
          render={({ field }) => (
            <button
              type="button"
              role="switch"
              aria-checked={field.value}
              onClick={() => field.onChange(!field.value)}
              className={cn(
                "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-2",
                field.value ? "bg-primary-600" : "bg-[hsl(var(--muted))]",
              )}
            >
              <span
                className={cn(
                  "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
                  field.value ? "translate-x-4" : "translate-x-0",
                )}
              />
            </button>
          )}
        />
        <span className="text-sm text-foreground">
          Cancelado por el paciente
        </span>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
          disabled={isPending}
          className="flex-1"
        >
          Volver
        </Button>
        <Button
          type="submit"
          variant="destructive"
          size="sm"
          disabled={isPending}
          className="flex-1"
        >
          {isPending ? (
            <span className="flex items-center gap-1.5">
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Cancelando...
            </span>
          ) : (
            "Cancelar cita"
          )}
        </Button>
      </div>
    </form>
  );
}

// ─── Complete form ────────────────────────────────────────────────────────────

interface CompleteFormProps {
  appointmentId: string;
  onDone: () => void;
}

function CompleteForm({ appointmentId, onDone }: CompleteFormProps) {
  const { mutate: complete, isPending } = useCompleteAppointment();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<AppointmentCompleteForm>({
    resolver: zodResolver(appointmentCompleteSchema),
  });

  const watchedNotes = watch("notes");

  function on_submit(values: AppointmentCompleteForm) {
    complete(
      { id: appointmentId, notes: values.notes },
      { onSuccess: onDone },
    );
  }

  return (
    <form onSubmit={handleSubmit(on_submit)} className="space-y-4 pt-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-green-700 dark:text-green-400">
        <Check className="h-4 w-4 shrink-0" />
        Completar consulta
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="completion_notes" className="text-sm font-medium">
          Notas de cierre{" "}
          <span className="text-[hsl(var(--muted-foreground))] font-normal">
            (opcional)
          </span>
        </Label>
        <textarea
          id="completion_notes"
          rows={3}
          placeholder="Observaciones finales, indicaciones, próximos pasos..."
          {...register("notes")}
          className="w-full resize-none rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] px-3 py-2 text-sm placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0"
          aria-invalid={Boolean(errors.notes)}
        />
        <div className="flex items-center justify-between text-xs text-[hsl(var(--muted-foreground))]">
          <span>
            {errors.notes ? errors.notes.message : "Máximo 1000 caracteres"}
          </span>
          <span className="tabular-nums">
            {(watchedNotes ?? "").length}/1000
          </span>
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onDone}
          disabled={isPending}
          className="flex-1"
        >
          Volver
        </Button>
        <Button
          type="submit"
          size="sm"
          disabled={isPending}
          className="flex-1 bg-green-600 hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600"
        >
          {isPending ? (
            <span className="flex items-center gap-1.5">
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Completando...
            </span>
          ) : (
            "Confirmar cierre"
          )}
        </Button>
      </div>
    </form>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

/**
 * Appointment detail modal (spec FE-AG-03).
 *
 * Shows full appointment details (patient, doctor, date/time, type, status)
 * and contextual action buttons based on the current status:
 *
 * - scheduled  → Confirmar | Cancelar
 * - confirmed  → Iniciar consulta | Completar | Cancelar | No asistió
 * - in_progress → Completar consulta | Cancelar
 * - completed  → View only
 * - cancelled  → View only (shows reason)
 * - no_show    → View only
 *
 * Cancel and complete actions expand inline forms rather than opening
 * additional dialogs, keeping everything in one focused context.
 *
 * @example
 * <AppointmentDetailModal
 *   appointmentId={selectedId}
 *   open={panelOpen}
 *   onOpenChange={setPanelOpen}
 * />
 */
function AppointmentDetailModal({
  appointmentId,
  open,
  onOpenChange,
}: AppointmentDetailModalProps) {
  // ─── Inline form mode ─────────────────────────────────────────────────────
  const [inline_mode, set_inline_mode] = React.useState<
    "idle" | "cancel" | "complete"
  >("idle");

  // ─── Data ─────────────────────────────────────────────────────────────────
  const {
    data: appointment,
    isLoading,
    isError,
    refetch,
  } = useAppointment(open ? appointmentId : null);

  // ─── Action mutations ─────────────────────────────────────────────────────
  const { mutate: confirm, isPending: is_confirming } = useConfirmAppointment();
  const { mutate: start, isPending: is_starting } = useStartAppointment();
  const { mutate: record_no_show, isPending: is_no_showing } = useNoShow();

  const is_any_action_pending = is_confirming || is_starting || is_no_showing;

  // ─── Reset inline mode when modal closes or appointment changes ───────────
  React.useEffect(() => {
    if (!open) {
      set_inline_mode("idle");
    }
  }, [open, appointmentId]);

  // ─── Derived values ───────────────────────────────────────────────────────
  const status = appointment?.status as AppointmentStatus | undefined;
  const is_terminal = status ? TERMINAL_STATUSES.includes(status) : false;

  // ─── Render helpers ───────────────────────────────────────────────────────

  function render_patient_card(appt: Appointment) {
    const display_name = appt.patient_name ?? "Paciente";
    const initials = display_name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase() ?? "")
      .join("");

    return (
      <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/30 p-4">
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 text-base font-bold">
            {initials}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-foreground leading-tight">
              {display_name}
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
              ID: {appt.patient_id}
            </p>
          </div>
        </div>
      </div>
    );
  }

  function render_meta_block(appt: Appointment) {
    const time_range = format_appointment_range(
      appt.start_time,
      appt.duration_minutes,
    );

    return (
      <dl className="space-y-2.5 text-sm">
        <div className="flex items-start justify-between gap-4">
          <dt className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))] shrink-0">
            <User className="h-3.5 w-3.5" />
            Doctor
          </dt>
          <dd className="font-medium text-right">
            {appt.doctor_name ?? "—"}
          </dd>
        </div>

        <div className="flex items-start justify-between gap-4">
          <dt className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))] shrink-0">
            <Calendar className="h-3.5 w-3.5" />
            Fecha
          </dt>
          <dd className="font-medium text-right">{time_range}</dd>
        </div>

        <div className="flex items-start justify-between gap-4">
          <dt className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))] shrink-0">
            <Clock className="h-3.5 w-3.5" />
            Duración
          </dt>
          <dd className="font-medium">{appt.duration_minutes} minutos</dd>
        </div>
      </dl>
    );
  }

  function render_notes(appt: Appointment) {
    const notes = appt.completion_notes ?? appt.notes;

    if (!notes) {
      return (
        <p className="text-sm italic text-[hsl(var(--muted-foreground))]">
          Sin notas registradas.
        </p>
      );
    }

    return (
      <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
        {notes}
      </p>
    );
  }

  function render_cancellation_reason(appt: Appointment) {
    if (!appt.cancellation_reason) return null;

    const label =
      CANCELLATION_REASON_LABELS[
        appt.cancellation_reason as keyof typeof CANCELLATION_REASON_LABELS
      ] ?? appt.cancellation_reason;

    return (
      <div className="rounded-lg border border-destructive-200 dark:border-destructive-800 bg-destructive-50 dark:bg-destructive-950/30 px-3 py-2.5 text-sm">
        <span className="font-medium text-destructive-700 dark:text-destructive-400">
          Motivo de cancelación:{" "}
        </span>
        <span className="text-destructive-600 dark:text-destructive-300">
          {label}
        </span>
      </div>
    );
  }

  function render_action_buttons(appt: Appointment) {
    if (is_terminal) return null;
    if (inline_mode !== "idle") return null;

    const s = appt.status as AppointmentStatus;

    return (
      <div className="space-y-2.5">
        {/* Primary action */}
        {s === "scheduled" && (
          <Button
            className="w-full h-11 bg-green-600 hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600 text-white"
            onClick={() => confirm(appt.id)}
            disabled={is_any_action_pending}
            aria-label={`Confirmar cita de ${appt.patient_name ?? "Paciente"}`}
          >
            {is_confirming ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Confirmando...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Check className="h-4 w-4" />
                Confirmar cita
              </span>
            )}
          </Button>
        )}

        {s === "confirmed" && (
          <Button
            className="w-full h-11"
            onClick={() => start(appt.id)}
            disabled={is_any_action_pending}
            aria-label={`Iniciar consulta de ${appt.patient_name ?? "paciente"}`}
          >
            {is_starting ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Iniciando...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Play className="h-4 w-4" />
                Iniciar consulta
              </span>
            )}
          </Button>
        )}

        {s === "in_progress" && (
          <Button
            className="w-full h-11 bg-green-600 hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600 text-white"
            onClick={() => set_inline_mode("complete")}
            disabled={is_any_action_pending}
            aria-label={`Completar consulta de ${appt.patient_name ?? "Paciente"}`}
          >
            <span className="flex items-center gap-2">
              <Check className="h-4 w-4" />
              Completar consulta
            </span>
          </Button>
        )}

        {/* Secondary actions row */}
        <div className="flex items-center gap-2">
          {/* Complete — available from confirmed status too */}
          {s === "confirmed" && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 text-green-700 border-green-300 hover:bg-green-50 dark:text-green-400 dark:border-green-700 dark:hover:bg-green-950/40"
              onClick={() => set_inline_mode("complete")}
              disabled={is_any_action_pending}
              aria-label="Completar consulta directamente"
            >
              <Check className="h-3.5 w-3.5 mr-1.5" />
              Completar
            </Button>
          )}

          {/* No-show — only for scheduled/confirmed */}
          {(s === "scheduled" || s === "confirmed") && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 text-amber-700 border-amber-300 hover:bg-amber-50 dark:text-amber-400 dark:border-amber-700 dark:hover:bg-amber-950/40"
              onClick={() => record_no_show(appt.id)}
              disabled={is_any_action_pending}
              aria-label={`Registrar inasistencia de ${appt.patient_name ?? "Paciente"}`}
            >
              {is_no_showing ? (
                <span className="flex items-center gap-1.5">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
                  Registrando...
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <UserX className="h-3.5 w-3.5" />
                  No asistió
                </span>
              )}
            </Button>
          )}

          {/* Cancel */}
          {!is_terminal && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 text-destructive-700 border-destructive-300 hover:bg-destructive-50 dark:text-destructive-400 dark:border-destructive-700 dark:hover:bg-destructive-950/40"
              onClick={() => set_inline_mode("cancel")}
              disabled={is_any_action_pending}
              aria-label="Cancelar esta cita"
            >
              <Ban className="h-3.5 w-3.5 mr-1.5" />
              Cancelar cita
            </Button>
          )}
        </div>
      </div>
    );
  }

  // ─── Full render ──────────────────────────────────────────────────────────

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md w-full p-0 gap-0 overflow-hidden"
        aria-label="Detalle de cita"
      >
        {/* ─── Header ───────────────────────────────────────────────────── */}
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-[hsl(var(--border))]">
          <DialogTitle className="text-lg font-bold flex items-center gap-2">
            <Stethoscope className="h-5 w-5 text-primary-600" />
            Detalle de Cita
          </DialogTitle>
          <DialogDescription className="sr-only">
            Información completa de la cita y acciones disponibles según su
            estado actual.
          </DialogDescription>

          {/* Status + type badges */}
          {appointment && (
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <AppointmentStatusBadge status={appointment.status} />
              <AppointmentTypeBadge type={appointment.type} />
            </div>
          )}

          {isLoading && (
            <div className="flex gap-2 mt-2">
              <Skeleton className="h-6 w-24 rounded-full" />
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
          )}
        </DialogHeader>

        {/* ─── Body ─────────────────────────────────────────────────────── */}
        <div className="max-h-[calc(80vh-100px)] overflow-y-auto">
          {/* Loading state */}
          {isLoading && <AppointmentDetailSkeleton />}

          {/* Error state */}
          {isError && !isLoading && (
            <div className="px-6 py-8 flex flex-col items-center gap-3 text-center">
              <AlertTriangle className="h-8 w-8 text-destructive-500" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No se pudo cargar la cita.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
              >
                Reintentar
              </Button>
            </div>
          )}

          {/* Appointment loaded */}
          {appointment && !isLoading && (
            <div className="px-6 py-5 space-y-5">

              {/* Patient card */}
              {render_patient_card(appointment)}

              {/* Meta block */}
              {render_meta_block(appointment)}

              <Separator />

              {/* Notes / cancellation info */}
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                  {appointment.status === "cancelled"
                    ? "Información de cancelación"
                    : appointment.status === "completed"
                      ? "Notas de cierre"
                      : "Notas"}
                </p>

                {appointment.status === "cancelled" &&
                  render_cancellation_reason(appointment)}

                {render_notes(appointment)}
              </div>

              {/* Inline forms */}
              {inline_mode === "cancel" && !is_terminal && (
                <>
                  <Separator />
                  <CancelForm
                    appointmentId={appointment.id}
                    onCancel={() => set_inline_mode("idle")}
                  />
                </>
              )}

              {inline_mode === "complete" && !is_terminal && (
                <>
                  <Separator />
                  <CompleteForm
                    appointmentId={appointment.id}
                    onDone={() => set_inline_mode("idle")}
                  />
                </>
              )}

              {/* Action buttons — shown only in idle mode */}
              {inline_mode === "idle" && (
                <>
                  {!is_terminal && <Separator />}
                  {render_action_buttons(appointment)}
                </>
              )}

              {/* Terminal status — no-show extra info */}
              {appointment.status === "no_show" && (
                <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 px-3 py-2.5 text-sm text-amber-700 dark:text-amber-300">
                  El paciente no asistió a esta cita.
                </div>
              )}
            </div>
          )}
        </div>

        {/* ─── Close button helper text for terminal appointments ─────────── */}
        {appointment && is_terminal && (
          <div className="px-6 pb-5">
            <Button
              variant="outline"
              className="w-full"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4 mr-2" />
              Cerrar
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

AppointmentDetailModal.displayName = "AppointmentDetailModal";

export { AppointmentDetailModal };
