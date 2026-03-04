"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TimeGridProps {
  /** First hour of the grid (inclusive). Default: 7 */
  startHour?: number;
  /** Last hour of the grid (inclusive). Default: 21 */
  endHour?: number;
  /** Interval between time slots in minutes. Default: 30 */
  intervalMinutes?: number;
  className?: string;
  /** Appointment blocks rendered as absolute-positioned children */
  children?: React.ReactNode;
  /** Called when an empty time slot is clicked. Receives ISO-like "HH:MM" string. */
  onSlotClick?: (time: string) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

/** Height in pixels for one hour on the time grid */
const HOUR_HEIGHT_PX = 60;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function padTwo(n: number): string {
  return n.toString().padStart(2, "0");
}

function formatHourLabel(hour: number): string {
  const h = hour % 12 || 12;
  const ampm = hour < 12 ? "a.m." : "p.m.";
  return `${h}:00 ${ampm}`;
}

/**
 * Generates the list of time slot labels for a given range and interval.
 * e.g. startHour=7, endHour=21, intervalMinutes=30 →
 *   [ "07:00", "07:30", "08:00", ... "21:00" ]
 */
function generateTimeSlots(
  startHour: number,
  endHour: number,
  intervalMinutes: number,
): string[] {
  const slots: string[] = [];
  const total_minutes = (endHour - startHour) * 60;

  for (let m = 0; m <= total_minutes; m += intervalMinutes) {
    const hour = startHour + Math.floor(m / 60);
    const minute = m % 60;
    slots.push(`${padTwo(hour)}:${padTwo(minute)}`);
  }
  return slots;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Vertical time grid with clickable slots.
 * Children are rendered as absolute-positioned overlays (appointment blocks).
 *
 * Total height = (endHour - startHour) * HOUR_HEIGHT_PX = (21-7)*60 = 840px by default.
 *
 * Parent components (DayColumn, WeekView) should use CSS calc to position
 * appointment blocks:
 *   top: ((startMinuteOffsetFromGridStart) / 60) * HOUR_HEIGHT_PX
 *   height: (durationMinutes / 60) * HOUR_HEIGHT_PX
 *
 * @example
 * <TimeGrid onSlotClick={(time) => openCreateModal(time)}>
 *   <AppointmentBlock ... />
 * </TimeGrid>
 */
export function TimeGrid({
  startHour = 7,
  endHour = 21,
  intervalMinutes = 30,
  className,
  children,
  onSlotClick,
}: TimeGridProps) {
  const slots = generateTimeSlots(startHour, endHour, intervalMinutes);
  const total_hours = endHour - startHour;
  const grid_height = total_hours * HOUR_HEIGHT_PX;

  // Build hour-level slot labels (only show whole hours on the left gutter)
  const hour_labels = Array.from({ length: total_hours + 1 }, (_, i) => startHour + i);

  function handleSlotClick(slotTime: string) {
    onSlotClick?.(slotTime);
  }

  return (
    <div className={cn("flex w-full select-none", className)}>
      {/* ─── Time Labels Gutter ─────────────────────────────────────────────── */}
      <div
        className="flex-shrink-0 w-14 relative"
        style={{ height: grid_height }}
        aria-hidden="true"
      >
        {hour_labels.map((hour) => (
          <div
            key={hour}
            className="absolute right-2 -translate-y-[9px] text-[10px] leading-none text-[hsl(var(--muted-foreground))] font-medium tabular-nums"
            style={{ top: (hour - startHour) * HOUR_HEIGHT_PX }}
          >
            {formatHourLabel(hour)}
          </div>
        ))}
      </div>

      {/* ─── Grid Body ──────────────────────────────────────────────────────── */}
      <div
        className="relative flex-1 border-l border-[hsl(var(--border))]"
        style={{ height: grid_height }}
      >
        {/* Horizontal grid lines for each slot */}
        {slots.map((slot, idx) => {
          const is_hour_mark = slot.endsWith(":00");
          const top_px = (idx * intervalMinutes * HOUR_HEIGHT_PX) / 60;

          return (
            <div
              key={slot}
              className={cn(
                "absolute left-0 right-0",
                is_hour_mark
                  ? "border-t border-[hsl(var(--border))]"
                  : "border-t border-dashed border-[hsl(var(--border))]/40",
              )}
              style={{ top: top_px }}
            />
          );
        })}

        {/* Clickable slot areas — one per interval */}
        {slots.slice(0, -1).map((slot, idx) => {
          const top_px = (idx * intervalMinutes * HOUR_HEIGHT_PX) / 60;
          const height_px = (intervalMinutes * HOUR_HEIGHT_PX) / 60;

          return (
            <button
              key={`btn-${slot}`}
              type="button"
              className={cn(
                "absolute left-0 right-0 cursor-pointer",
                "hover:bg-primary-50/60 dark:hover:bg-primary-900/10",
                "transition-colors duration-100",
                "focus:outline-none focus:bg-primary-50/80 dark:focus:bg-primary-900/20",
                "focus:ring-1 focus:ring-inset focus:ring-primary-300",
              )}
              style={{ top: top_px, height: height_px }}
              onClick={() => handleSlotClick(slot)}
              aria-label={`Agendar a las ${slot}`}
            />
          );
        })}

        {/* Appointment blocks rendered on top */}
        {children}
      </div>
    </div>
  );
}

// ─── Exported Helpers ─────────────────────────────────────────────────────────

/**
 * Calculates the pixel offset from the top of the grid for a given ISO datetime.
 * Used by parent components to position appointment blocks.
 *
 * @param isoDatetime - ISO datetime string (e.g. "2026-03-01T09:30:00Z")
 * @param startHour - Grid start hour (default 7)
 * @returns top offset in pixels
 */
export function getTopOffset(isoDatetime: string, startHour = 7): number {
  const date = new Date(isoDatetime);
  const cotFormatter = new Intl.DateTimeFormat("es-CO", {
    timeZone: "America/Bogota",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  });
  const parts = cotFormatter.formatToParts(date);
  const h = Number(parts.find((p) => p.type === "hour")?.value ?? 0);
  const m = Number(parts.find((p) => p.type === "minute")?.value ?? 0);
  const hours = h + m / 60;
  const offset_from_start = hours - startHour;
  return Math.max(0, offset_from_start * HOUR_HEIGHT_PX);
}

/**
 * Calculates the height in pixels for a given duration.
 *
 * @param durationMinutes - Duration in minutes
 * @returns height in pixels
 */
export function getDurationHeight(durationMinutes: number): number {
  return (durationMinutes / 60) * HOUR_HEIGHT_PX;
}

export { HOUR_HEIGHT_PX };
