"use client";

import * as React from "react";
import { Plus, Trash2, ChevronDown, ChevronUp, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/hooks/use-auth";
import {
  useDoctorSchedule,
  useUpdateSchedule,
  type BreakSlot,
  type ScheduleDay,
} from "@/lib/hooks/use-schedule";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const DAY_LABELS: Record<number, string> = {
  0: "Lunes",
  1: "Martes",
  2: "Miércoles",
  3: "Jueves",
  4: "Viernes",
  5: "Sábado",
  6: "Domingo",
};

/** Default empty schedule for a new doctor who has never configured their hours */
function buildDefaultSchedule(): ScheduleDay[] {
  return Array.from({ length: 7 }, (_, i) => ({
    day_of_week: i,
    is_working: i < 5, // Monday–Friday working by default
    start_time: i < 5 ? "08:00" : null,
    end_time: i < 5 ? "17:00" : null,
    breaks: [],
    appointment_duration_defaults: {},
  }));
}

// ─── Break slot sub-component ─────────────────────────────────────────────────

interface BreakRowProps {
  break_slot: BreakSlot;
  onChange: (updated: BreakSlot) => void;
  onRemove: () => void;
  disabled?: boolean;
}

function BreakRow({ break_slot, onChange, onRemove, disabled }: BreakRowProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1.5">
        <Input
          type="time"
          value={break_slot.start}
          onChange={(e) => onChange({ ...break_slot, start: e.target.value })}
          disabled={disabled}
          aria-label="Inicio del descanso"
          className="w-32"
        />
        <span className="text-sm text-[hsl(var(--muted-foreground))]">–</span>
        <Input
          type="time"
          value={break_slot.end}
          onChange={(e) => onChange({ ...break_slot, end: e.target.value })}
          disabled={disabled}
          aria-label="Fin del descanso"
          className="w-32"
        />
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onRemove}
        disabled={disabled}
        aria-label="Eliminar descanso"
        className="h-8 w-8 p-0 text-[hsl(var(--muted-foreground))] hover:text-destructive-600"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

// ─── Day row sub-component ────────────────────────────────────────────────────

interface DayRowProps {
  day: ScheduleDay;
  onChange: (updated: ScheduleDay) => void;
  canEdit: boolean;
}

function DayRow({ day, onChange, canEdit }: DayRowProps) {
  const [showDurations, setShowDurations] = React.useState(false);

  function toggleWorking() {
    if (!canEdit) return;
    if (day.is_working) {
      onChange({
        ...day,
        is_working: false,
        start_time: null,
        end_time: null,
        breaks: [],
      });
    } else {
      onChange({
        ...day,
        is_working: true,
        start_time: "08:00",
        end_time: "17:00",
      });
    }
  }

  function addBreak() {
    onChange({
      ...day,
      breaks: [...day.breaks, { start: "13:00", end: "14:00" }],
    });
  }

  function updateBreak(index: number, updated: BreakSlot) {
    const breaks = day.breaks.map((b, i) => (i === index ? updated : b));
    onChange({ ...day, breaks });
  }

  function removeBreak(index: number) {
    onChange({ ...day, breaks: day.breaks.filter((_, i) => i !== index) });
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-[hsl(var(--border))] p-4 transition-colors",
        day.is_working
          ? "bg-[hsl(var(--card))]"
          : "bg-[hsl(var(--muted))]/40 opacity-70",
      )}
    >
      {/* ─── Day header row ─────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Toggle switch (native checkbox styled) */}
        <button
          type="button"
          role="switch"
          aria-checked={day.is_working}
          aria-label={`${DAY_LABELS[day.day_of_week]} — ${day.is_working ? "día laboral" : "día no laboral"}`}
          onClick={toggleWorking}
          disabled={!canEdit}
          className={cn(
            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent",
            "transition-colors duration-200 ease-in-out",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
            day.is_working
              ? "bg-primary-600"
              : "bg-[hsl(var(--muted-foreground))]/40",
            !canEdit && "cursor-not-allowed opacity-50",
          )}
        >
          <span
            className={cn(
              "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200",
              day.is_working ? "translate-x-4" : "translate-x-0",
            )}
          />
        </button>

        {/* Day label */}
        <span className="w-24 text-sm font-medium text-foreground">
          {DAY_LABELS[day.day_of_week]}
        </span>

        {/* Time range — only visible when working */}
        {day.is_working && (
          <div className="flex items-center gap-2">
            <Input
              type="time"
              value={day.start_time ?? ""}
              onChange={(e) =>
                onChange({ ...day, start_time: e.target.value })
              }
              disabled={!canEdit}
              aria-label={`Hora de inicio — ${DAY_LABELS[day.day_of_week]}`}
              className="w-32 text-sm"
            />
            <span className="text-sm text-[hsl(var(--muted-foreground))]">–</span>
            <Input
              type="time"
              value={day.end_time ?? ""}
              onChange={(e) =>
                onChange({ ...day, end_time: e.target.value })
              }
              disabled={!canEdit}
              aria-label={`Hora de fin — ${DAY_LABELS[day.day_of_week]}`}
              className="w-32 text-sm"
            />
          </div>
        )}

        {!day.is_working && (
          <span className="text-xs text-[hsl(var(--muted-foreground))]">
            No laboral
          </span>
        )}
      </div>

      {/* ─── Breaks ─────────────────────────────────────────────────────── */}
      {day.is_working && (
        <div className="mt-3 space-y-2 pl-12">
          {day.breaks.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                Descansos
              </p>
              {day.breaks.map((b, idx) => (
                <BreakRow
                  key={idx}
                  break_slot={b}
                  onChange={(updated) => updateBreak(idx, updated)}
                  onRemove={() => removeBreak(idx)}
                  disabled={!canEdit}
                />
              ))}
            </div>
          )}

          {canEdit && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={addBreak}
              className="h-7 gap-1.5 px-2 text-xs text-[hsl(var(--muted-foreground))] hover:text-foreground"
            >
              <Plus className="h-3 w-3" />
              Agregar descanso
            </Button>
          )}

          {/* ─── Duration defaults (collapsible) ──────────────────────── */}
          <button
            type="button"
            onClick={() => setShowDurations((v) => !v)}
            className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors"
          >
            {showDurations ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            Duración predeterminada por tipo
          </button>

          {showDurations && (
            <div className="space-y-2 rounded-md border border-[hsl(var(--border))] p-3">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Minutos predeterminados por tipo de cita en este día. Deja en
                blanco para usar el global de la clínica.
              </p>
              {[
                { key: "consulta", label: "Consulta general" },
                { key: "limpieza", label: "Limpieza / Profilaxis" },
                { key: "ortodoncia", label: "Ortodoncia" },
                { key: "cirugia", label: "Cirugía oral" },
                { key: "urgencia", label: "Urgencia" },
              ].map(({ key, label }) => (
                <div key={key} className="flex items-center gap-3">
                  <Label
                    htmlFor={`dur-${day.day_of_week}-${key}`}
                    className="w-36 text-xs"
                  >
                    {label}
                  </Label>
                  <Input
                    id={`dur-${day.day_of_week}-${key}`}
                    type="number"
                    min={5}
                    max={240}
                    step={5}
                    placeholder="—"
                    value={
                      day.appointment_duration_defaults[key] !== undefined
                        ? String(day.appointment_duration_defaults[key])
                        : ""
                    }
                    onChange={(e) => {
                      const val = e.target.value === "" ? undefined : Number(e.target.value);
                      const updated = { ...day.appointment_duration_defaults };
                      if (val === undefined) {
                        delete updated[key];
                      } else {
                        updated[key] = val;
                      }
                      onChange({ ...day, appointment_duration_defaults: updated });
                    }}
                    disabled={!canEdit}
                    className="w-24 text-sm"
                  />
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">min</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function ScheduleSkeleton() {
  return (
    <div className="max-w-3xl space-y-6">
      <div className="space-y-1">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: 7 }, (_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ScheduleSettingsPage() {
  const { user, has_role } = useAuth();
  const canEdit = has_role("clinic_owner", "doctor");

  const { data: serverSchedule, isLoading } = useDoctorSchedule(user?.id);
  const { mutate: updateSchedule, isPending } = useUpdateSchedule();

  // Local copy of schedule that the user edits before saving
  const [schedule, setSchedule] = React.useState<ScheduleDay[]>([]);
  const [isDirty, setIsDirty] = React.useState(false);

  // Initialize local state once server data loads
  React.useEffect(() => {
    if (serverSchedule) {
      // Sort by day_of_week to guarantee order
      const sorted = [...serverSchedule.schedule].sort(
        (a, b) => a.day_of_week - b.day_of_week,
      );
      setSchedule(sorted);
    } else if (!isLoading) {
      // No schedule configured yet — seed with sensible defaults
      setSchedule(buildDefaultSchedule());
    }
    setIsDirty(false);
  }, [serverSchedule, isLoading]);

  function handleDayChange(updated: ScheduleDay) {
    setSchedule((prev) =>
      prev.map((d) => (d.day_of_week === updated.day_of_week ? updated : d)),
    );
    setIsDirty(true);
  }

  function handleSave() {
    if (!user) return;
    updateSchedule(
      { doctorId: user.id, schedule },
      { onSuccess: () => setIsDirty(false) },
    );
  }

  if (isLoading) return <ScheduleSkeleton />;

  return (
    <div className="max-w-3xl space-y-6">
      {/* ─── Page header ────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Horario de atención
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Configura los días y horas en que estás disponible para citas. Los
          cambios aplican a partir del siguiente día laborable.
        </p>
      </div>

      {/* Read-only notice */}
      {!canEdit && (
        <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
          <Lock className="h-4 w-4 shrink-0" />
          Solo el médico o el propietario de la clínica puede modificar este horario.
        </div>
      )}

      {/* ─── Weekly grid card ────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Semana laboral</CardTitle>
          <CardDescription>
            Activa o desactiva cada día y define el horario y los descansos.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {schedule.map((day) => (
            <DayRow
              key={day.day_of_week}
              day={day}
              onChange={handleDayChange}
              canEdit={canEdit}
            />
          ))}
        </CardContent>
      </Card>

      <Separator />

      {/* ─── Save button ─────────────────────────────────────────────────── */}
      {canEdit && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            {isDirty
              ? "Tienes cambios sin guardar."
              : "El horario está actualizado."}
          </p>
          <Button
            type="button"
            onClick={handleSave}
            disabled={isPending || !isDirty}
          >
            {isPending ? "Guardando..." : "Guardar horario"}
          </Button>
        </div>
      )}
    </div>
  );
}
