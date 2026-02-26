"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, Plus, CalendarDays, LayoutList } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatTime, formatDate } from "@/lib/utils";
import { useCalendar, type CalendarSlot } from "@/lib/hooks/use-appointments";
import { TimeGrid, getTopOffset, getDurationHeight } from "@/components/agenda/time-grid";
import {
  STATUS_COLORS,
  AppointmentStatusBadge,
  AppointmentTypeBadge,
} from "@/components/agenda/appointment-status-badge";
import {
  APPOINTMENT_TYPE_LABELS,
  APPOINTMENT_STATUS_LABELS,
} from "@/lib/validations/appointment";

// ─── Types ────────────────────────────────────────────────────────────────────

export type CalendarView = "day" | "week" | "month";

export interface CalendarProps {
  /** Initial date to display. Defaults to today. */
  initialDate?: Date;
  /** Filter appointments to a specific doctor. */
  doctor_id?: string;
  /** Called when an appointment block is clicked. */
  onAppointmentClick?: (slot: CalendarSlot) => void;
  /** Called when an empty slot is clicked. Receives the ISO datetime string. */
  onSlotClick?: (isoDatetime: string) => void;
  /** Called when the create button is clicked. */
  onCreateClick?: () => void;
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function startOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  // Week starts Monday (1); Sunday is 0 → shift to -6
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d;
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function getDayRange(date: Date): { from: string; to: string } {
  return { from: toISODate(date), to: toISODate(date) };
}

function getWeekRange(date: Date): { from: string; to: string } {
  const mon = startOfWeek(date);
  const sun = addDays(mon, 6);
  return { from: toISODate(mon), to: toISODate(sun) };
}

function getMonthRange(date: Date): { from: string; to: string } {
  return {
    from: toISODate(startOfMonth(date)),
    to: toISODate(endOfMonth(date)),
  };
}

function getDateRange(view: CalendarView, date: Date): { from: string; to: string } {
  if (view === "day") return getDayRange(date);
  if (view === "week") return getWeekRange(date);
  return getMonthRange(date);
}

function getNavigationDelta(view: CalendarView): number {
  if (view === "day") return 1;
  if (view === "week") return 7;
  return 30; // month — approximate
}

function formatHeaderLabel(view: CalendarView, date: Date): string {
  if (view === "day") {
    return new Intl.DateTimeFormat("es-CO", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(date);
  }
  if (view === "week") {
    const mon = startOfWeek(date);
    const sun = addDays(mon, 6);
    const sameMonth = mon.getMonth() === sun.getMonth();
    if (sameMonth) {
      const monthYear = new Intl.DateTimeFormat("es-CO", {
        month: "long",
        year: "numeric",
      }).format(mon);
      return `${mon.getDate()} – ${sun.getDate()} de ${monthYear}`;
    }
    return `${formatDate(mon)} – ${formatDate(sun)}`;
  }
  // month
  return new Intl.DateTimeFormat("es-CO", {
    month: "long",
    year: "numeric",
  }).format(date);
}

function isToday(date: Date): boolean {
  const today = new Date();
  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  );
}

// ─── Appointment Block (Day/Week) ─────────────────────────────────────────────

interface AppointmentBlockProps {
  slot: CalendarSlot;
  gridStartHour?: number;
  onClick?: (slot: CalendarSlot) => void;
}

function AppointmentBlock({
  slot,
  gridStartHour = 7,
  onClick,
}: AppointmentBlockProps) {
  const colors = STATUS_COLORS[slot.status];
  const topPx = getTopOffset(slot.start_time, gridStartHour);
  const heightPx = Math.max(getDurationHeight(slot.duration_minutes), 24);
  const isShort = heightPx < 40;

  return (
    <button
      type="button"
      className={cn(
        "absolute left-1 right-1 rounded-md border px-1.5 py-1 text-left",
        "overflow-hidden cursor-pointer transition-all duration-150",
        "hover:shadow-md hover:z-10 hover:scale-[1.01]",
        "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-1",
        "z-[1]",
        colors.bg,
        colors.border,
        colors.text,
      )}
      style={{ top: topPx, height: heightPx }}
      onClick={() => onClick?.(slot)}
      aria-label={`Cita: ${slot.patient_name ?? "Paciente"} a las ${formatTime(slot.start_time)}`}
    >
      {isShort ? (
        <p className="text-[10px] font-semibold leading-tight truncate">
          {slot.patient_name ?? "Paciente"}
        </p>
      ) : (
        <>
          <p className="text-xs font-semibold leading-tight truncate">
            {slot.patient_name ?? "Paciente"}
          </p>
          <p className="text-[10px] leading-tight mt-0.5 opacity-80">
            {formatTime(slot.start_time)} · {APPOINTMENT_TYPE_LABELS[slot.type]}
          </p>
        </>
      )}
    </button>
  );
}

// ─── Day View ─────────────────────────────────────────────────────────────────

interface DayViewProps {
  date: Date;
  slots: CalendarSlot[];
  onAppointmentClick?: (slot: CalendarSlot) => void;
  onSlotClick?: (isoDatetime: string) => void;
}

function DayView({ date, slots, onAppointmentClick, onSlotClick }: DayViewProps) {
  const dateStr = toISODate(date);
  const daySlots = slots.filter((s) => s.start_time.startsWith(dateStr));

  function handleSlotClick(time: string) {
    // Build a full ISO datetime: "YYYY-MM-DDTHH:MM:00"
    onSlotClick?.(`${dateStr}T${time}:00`);
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <TimeGrid onSlotClick={handleSlotClick} className="min-h-full">
        {daySlots.map((slot) => (
          <AppointmentBlock
            key={slot.id}
            slot={slot}
            onClick={onAppointmentClick}
          />
        ))}
      </TimeGrid>
    </div>
  );
}

// ─── Week View ────────────────────────────────────────────────────────────────

const WEEK_DAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

interface WeekViewProps {
  weekStart: Date;
  slots: CalendarSlot[];
  onAppointmentClick?: (slot: CalendarSlot) => void;
  onSlotClick?: (isoDatetime: string) => void;
}

function WeekView({ weekStart, slots, onAppointmentClick, onSlotClick }: WeekViewProps) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  return (
    <div className="flex-1 overflow-auto">
      {/* Day headers */}
      <div className="sticky top-0 z-10 flex border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]">
        {/* Gutter space matching time label width */}
        <div className="w-14 shrink-0" />
        {days.map((day, idx) => (
          <div
            key={toISODate(day)}
            className={cn(
              "flex-1 py-2 text-center border-l border-[hsl(var(--border))]",
              "text-xs font-medium",
            )}
          >
            <span className="text-[hsl(var(--muted-foreground))]">
              {WEEK_DAY_LABELS[idx]}
            </span>
            <span
              className={cn(
                "ml-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-sm font-semibold",
                isToday(day)
                  ? "bg-primary-600 text-white"
                  : "text-foreground",
              )}
            >
              {day.getDate()}
            </span>
          </div>
        ))}
      </div>

      {/* Time grid columns */}
      <div className="flex">
        {/* Shared time labels */}
        <div className="w-14 shrink-0 relative" style={{ height: 840 }} aria-hidden="true">
          {Array.from({ length: 15 }, (_, i) => 7 + i).map((hour) => (
            <div
              key={hour}
              className="absolute right-2 -translate-y-[9px] text-[10px] leading-none text-[hsl(var(--muted-foreground))] font-medium tabular-nums"
              style={{ top: (hour - 7) * 60 }}
            >
              {hour % 12 || 12}{hour < 12 ? "a" : "p"}
            </div>
          ))}
        </div>

        {/* One column per day */}
        {days.map((day) => {
          const dateStr = toISODate(day);
          const daySlots = slots.filter((s) => s.start_time.startsWith(dateStr));

          return (
            <div
              key={dateStr}
              className={cn(
                "flex-1 relative border-l border-[hsl(var(--border))]",
                isToday(day) && "bg-primary-50/20 dark:bg-primary-900/5",
              )}
              style={{ height: 840 }}
            >
              {/* Grid lines */}
              {Array.from({ length: 29 }, (_, i) => i).map((idx) => (
                <div
                  key={idx}
                  className={cn(
                    "absolute left-0 right-0",
                    idx % 2 === 0
                      ? "border-t border-[hsl(var(--border))]"
                      : "border-t border-dashed border-[hsl(var(--border))]/40",
                  )}
                  style={{ top: idx * 30 }}
                />
              ))}

              {/* Clickable slot overlay */}
              {Array.from({ length: 28 }, (_, i) => i).map((idx) => {
                const hour = 7 + Math.floor((idx * 30) / 60);
                const minute = (idx * 30) % 60;
                const time = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
                return (
                  <button
                    key={`slot-${idx}`}
                    type="button"
                    className="absolute left-0 right-0 hover:bg-primary-50/60 dark:hover:bg-primary-900/10 transition-colors cursor-pointer focus:outline-none"
                    style={{ top: idx * 30, height: 30 }}
                    onClick={() => onSlotClick?.(`${dateStr}T${time}:00`)}
                    aria-label={`Agendar el ${dateStr} a las ${time}`}
                  />
                );
              })}

              {/* Appointment blocks */}
              {daySlots.map((slot) => (
                <AppointmentBlock
                  key={slot.id}
                  slot={slot}
                  onClick={onAppointmentClick}
                />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Month View ───────────────────────────────────────────────────────────────

interface MonthViewProps {
  date: Date;
  slots: CalendarSlot[];
  onAppointmentClick?: (slot: CalendarSlot) => void;
  onSlotClick?: (isoDatetime: string) => void;
}

function MonthView({ date, slots, onAppointmentClick, onSlotClick }: MonthViewProps) {
  const year = date.getFullYear();
  const month = date.getMonth();

  const first_day = new Date(year, month, 1);
  const last_day = new Date(year, month + 1, 0);

  // Monday-first grid: find how many leading empty cells before the 1st
  const leading_blanks = (first_day.getDay() + 6) % 7; // Mon=0 … Sun=6
  const total_cells = leading_blanks + last_day.getDate();
  const trailing_blanks =
    total_cells % 7 === 0 ? 0 : 7 - (total_cells % 7);

  const cells: Array<Date | null> = [
    ...Array(leading_blanks).fill(null),
    ...Array.from({ length: last_day.getDate() }, (_, i) => new Date(year, month, i + 1)),
    ...Array(trailing_blanks).fill(null),
  ];

  function getSlotsForDate(d: Date): CalendarSlot[] {
    const iso = toISODate(d);
    return slots.filter((s) => s.start_time.startsWith(iso));
  }

  return (
    <div className="flex-1 overflow-auto">
      {/* Weekday headers */}
      <div className="grid grid-cols-7 border-b border-[hsl(var(--border))]">
        {WEEK_DAY_LABELS.map((label) => (
          <div
            key={label}
            className="py-2 text-center text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            {label}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 flex-1">
        {cells.map((day, idx) => {
          if (!day) {
            return (
              <div
                key={`blank-${idx}`}
                className="min-h-[100px] border-b border-r border-[hsl(var(--border))] bg-[hsl(var(--muted))]/30"
              />
            );
          }

          const day_slots = getSlotsForDate(day);
          const is_today = isToday(day);
          const is_current_month = day.getMonth() === month;

          return (
            <button
              key={toISODate(day)}
              type="button"
              className={cn(
                "min-h-[100px] border-b border-r border-[hsl(var(--border))]",
                "p-1.5 text-left align-top cursor-pointer",
                "hover:bg-[hsl(var(--muted))]/40 transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-300",
                !is_current_month && "opacity-40",
              )}
              onClick={() => onSlotClick?.(`${toISODate(day)}T09:00:00`)}
              aria-label={`${formatDate(day)}, ${day_slots.length} citas`}
            >
              {/* Day number */}
              <span
                className={cn(
                  "inline-flex h-6 w-6 items-center justify-center rounded-full",
                  "text-sm font-medium mb-1",
                  is_today
                    ? "bg-primary-600 text-white"
                    : "text-foreground",
                )}
              >
                {day.getDate()}
              </span>

              {/* Appointment pills (up to 3, then "+N más") */}
              <div className="space-y-0.5">
                {day_slots.slice(0, 3).map((slot) => {
                  const colors = STATUS_COLORS[slot.status];
                  return (
                    <button
                      key={slot.id}
                      type="button"
                      className={cn(
                        "w-full text-left px-1 py-0.5 rounded text-[10px] truncate",
                        "border transition-all hover:opacity-80",
                        colors.bg,
                        colors.text,
                        colors.border,
                      )}
                      onClick={(e) => {
                        e.stopPropagation();
                        onAppointmentClick?.(slot);
                      }}
                    >
                      {formatTime(slot.start_time)} {slot.patient_name}
                    </button>
                  );
                })}
                {day_slots.length > 3 && (
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))] pl-1">
                    +{day_slots.length - 3} más
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function CalendarSkeleton() {
  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-9 w-9 rounded-md" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-24 rounded-md" />
          <Skeleton className="h-9 w-32 rounded-md" />
          <Skeleton className="h-9 w-36 rounded-md" />
        </div>
      </div>
      <Skeleton className="flex-1 w-full rounded-lg min-h-[500px]" />
    </div>
  );
}

// ─── Main Calendar Component ──────────────────────────────────────────────────

/**
 * Full-featured agenda calendar with day, week, and month views.
 *
 * Manages its own date navigation state. The parent is responsible for
 * handling slot clicks (create modal) and appointment clicks (detail modal).
 *
 * @example
 * <Calendar
 *   onAppointmentClick={(slot) => setSelectedAppointmentId(slot.id)}
 *   onSlotClick={(dt) => setCreateModalOpen(true)}
 *   onCreateClick={() => setCreateModalOpen(true)}
 * />
 */
export function Calendar({
  initialDate,
  doctor_id,
  onAppointmentClick,
  onSlotClick,
  onCreateClick,
  className,
}: CalendarProps) {
  const [view, setView] = React.useState<CalendarView>("day");
  const [currentDate, setCurrentDate] = React.useState<Date>(
    initialDate ?? new Date(),
  );

  const { from, to } = getDateRange(view, currentDate);

  const { data: calendar_data, isLoading } = useCalendar({
    date_from: from,
    date_to: to,
    doctor_id,
  });

  // Flatten all slots from the calendar response
  const all_slots = React.useMemo(() => {
    if (!calendar_data?.dates) return [];
    return Object.values(calendar_data.dates).flat();
  }, [calendar_data]);

  function handlePrev() {
    const delta = getNavigationDelta(view);
    setCurrentDate((d) => addDays(d, -delta));
  }

  function handleNext() {
    const delta = getNavigationDelta(view);
    setCurrentDate((d) => addDays(d, delta));
  }

  function handleToday() {
    setCurrentDate(new Date());
  }

  const headerLabel = formatHeaderLabel(view, currentDate);

  if (isLoading) {
    return <CalendarSkeleton />;
  }

  return (
    <div className={cn("flex flex-col h-full gap-0", className)}>
      {/* ─── Toolbar ────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[hsl(var(--border))]">
        {/* Navigation */}
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={handlePrev}
            aria-label="Período anterior"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <h2 className="px-2 text-sm font-semibold text-foreground min-w-[180px] text-center capitalize">
            {headerLabel}
          </h2>

          <Button
            variant="outline"
            size="icon"
            onClick={handleNext}
            aria-label="Período siguiente"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleToday}>
            Hoy
          </Button>

          <Select value={view} onValueChange={(v) => setView(v as CalendarView)}>
            <SelectTrigger className="w-36 h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="day">
                <span className="flex items-center gap-1.5">
                  <LayoutList className="h-3.5 w-3.5" />
                  Día
                </span>
              </SelectItem>
              <SelectItem value="week">
                <span className="flex items-center gap-1.5">
                  <CalendarDays className="h-3.5 w-3.5" />
                  Semana
                </span>
              </SelectItem>
              <SelectItem value="month">
                <span className="flex items-center gap-1.5">
                  <CalendarDays className="h-3.5 w-3.5" />
                  Mes
                </span>
              </SelectItem>
            </SelectContent>
          </Select>

          <Button size="sm" onClick={onCreateClick}>
            <Plus className="h-4 w-4 mr-1.5" />
            Nueva cita
          </Button>
        </div>
      </div>

      {/* ─── Calendar Body ──────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden pt-3">
        {view === "day" && (
          <DayView
            date={currentDate}
            slots={all_slots}
            onAppointmentClick={onAppointmentClick}
            onSlotClick={onSlotClick}
          />
        )}
        {view === "week" && (
          <WeekView
            weekStart={startOfWeek(currentDate)}
            slots={all_slots}
            onAppointmentClick={onAppointmentClick}
            onSlotClick={onSlotClick}
          />
        )}
        {view === "month" && (
          <MonthView
            date={currentDate}
            slots={all_slots}
            onAppointmentClick={onAppointmentClick}
            onSlotClick={onSlotClick}
          />
        )}
      </div>
    </div>
  );
}
