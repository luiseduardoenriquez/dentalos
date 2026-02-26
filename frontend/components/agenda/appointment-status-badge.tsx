"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { AppointmentStatus, AppointmentType } from "@/lib/validations/appointment";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AppointmentStatusBadgeProps {
  status: AppointmentStatus | string;
  className?: string;
}

export interface AppointmentTypeBadgeProps {
  type: AppointmentType | string;
  className?: string;
}

// ─── Status Color Map (for calendar block coloring) ──────────────────────────

/**
 * Maps appointment status to Tailwind classes for background, text, border, dot.
 * Used by the calendar time grid for appointment block rendering.
 */
export const STATUS_COLORS: Record<
  string,
  { bg: string; text: string; border: string; dot: string }
> = {
  scheduled: {
    bg: "bg-blue-50 dark:bg-blue-900/30",
    text: "text-blue-800 dark:text-blue-200",
    border: "border-blue-200 dark:border-blue-700",
    dot: "bg-blue-500",
  },
  confirmed: {
    bg: "bg-green-50 dark:bg-green-900/30",
    text: "text-green-800 dark:text-green-200",
    border: "border-green-200 dark:border-green-700",
    dot: "bg-green-500",
  },
  in_progress: {
    bg: "bg-amber-50 dark:bg-amber-900/30",
    text: "text-amber-800 dark:text-amber-200",
    border: "border-amber-200 dark:border-amber-700",
    dot: "bg-amber-500",
  },
  completed: {
    bg: "bg-slate-100 dark:bg-slate-800/50",
    text: "text-slate-600 dark:text-slate-300",
    border: "border-slate-200 dark:border-slate-700",
    dot: "bg-slate-400",
  },
  cancelled: {
    bg: "bg-red-50 dark:bg-red-900/20",
    text: "text-red-700 dark:text-red-300",
    border: "border-red-200 dark:border-red-800",
    dot: "bg-red-500",
  },
  no_show: {
    bg: "bg-orange-50 dark:bg-orange-900/20",
    text: "text-orange-700 dark:text-orange-300",
    border: "border-orange-200 dark:border-orange-800",
    dot: "bg-orange-500",
  },
};

// ─── Status Config ────────────────────────────────────────────────────────────

/**
 * Maps each appointment status to a Spanish label and Tailwind color classes.
 * Colors follow the spec (FE-AG-03): blue=scheduled, green=confirmed,
 * teal=in_progress, gray=completed, red=cancelled, amber=no_show.
 */
const STATUS_CONFIG: Record<
  string,
  { label: string; className: string }
> = {
  scheduled: {
    label: "Programada",
    className: [
      "border-blue-300 text-blue-700 bg-blue-50",
      "dark:border-blue-700 dark:text-blue-300 dark:bg-blue-950",
    ].join(" "),
  },
  confirmed: {
    label: "Confirmada",
    className: [
      "border-green-300 text-green-700 bg-green-50",
      "dark:border-green-700 dark:text-green-300 dark:bg-green-950",
    ].join(" "),
  },
  in_progress: {
    label: "En curso",
    className: [
      "border-teal-300 text-teal-700 bg-teal-50",
      "dark:border-teal-700 dark:text-teal-300 dark:bg-teal-950",
    ].join(" "),
  },
  completed: {
    label: "Completada",
    className: [
      "border-slate-300 text-slate-600 bg-slate-50",
      "dark:border-slate-600 dark:text-slate-300 dark:bg-slate-900",
    ].join(" "),
  },
  cancelled: {
    label: "Cancelada",
    className: [
      "border-red-300 text-red-700 bg-red-50",
      "dark:border-red-700 dark:text-red-300 dark:bg-red-950",
    ].join(" "),
  },
  no_show: {
    label: "No asistió",
    className: [
      "border-amber-300 text-amber-700 bg-amber-50",
      "dark:border-amber-700 dark:text-amber-300 dark:bg-amber-950",
    ].join(" "),
  },
};

// ─── Type Config ──────────────────────────────────────────────────────────────

/**
 * Maps appointment types to Spanish labels.
 * English API values → Spanish display labels (spec FE-AG-02).
 */
const TYPE_CONFIG: Record<string, { label: string }> = {
  consultation: { label: "Consulta" },
  procedure: { label: "Procedimiento" },
  emergency: { label: "Urgencia" },
  follow_up: { label: "Control" },
  // Legacy / alternate values from spec
  consulta: { label: "Consulta" },
  procedimiento: { label: "Procedimiento" },
  emergencia: { label: "Urgencia" },
  seguimiento: { label: "Control" },
  primera_vez: { label: "Primera vez" },
};

// ─── AppointmentStatusBadge ───────────────────────────────────────────────────

/**
 * Color-coded badge for appointment lifecycle status.
 * Renders a localized Spanish label with semantic background and border colors.
 *
 * @example
 * <AppointmentStatusBadge status="confirmed" />
 * // Renders: green "Confirmada" badge
 */
function AppointmentStatusBadge({ status, className }: AppointmentStatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  if (!config) {
    return (
      <Badge variant="outline" className={className}>
        {status}
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className={cn(config.className, className)}
    >
      {config.label}
    </Badge>
  );
}

AppointmentStatusBadge.displayName = "AppointmentStatusBadge";

// ─── AppointmentTypeBadge ─────────────────────────────────────────────────────

/**
 * Outlined badge for appointment type.
 * Translates English API values (consultation, procedure, emergency, follow_up)
 * to Spanish display labels.
 *
 * @example
 * <AppointmentTypeBadge type="procedure" />
 * // Renders: "Procedimiento" badge
 */
function AppointmentTypeBadge({ type, className }: AppointmentTypeBadgeProps) {
  const config = TYPE_CONFIG[type];

  if (!config) {
    return (
      <Badge variant="outline" className={className}>
        {type}
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className={cn("border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300", className)}>
      {config.label}
    </Badge>
  );
}

AppointmentTypeBadge.displayName = "AppointmentTypeBadge";

// ─── Exports ──────────────────────────────────────────────────────────────────

export { AppointmentStatusBadge, AppointmentTypeBadge };
