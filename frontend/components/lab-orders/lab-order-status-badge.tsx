"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface LabOrderStatusBadgeProps {
  status: string;
  className?: string;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  string,
  { label: string; className: string }
> = {
  pending: {
    label: "Pendiente",
    className:
      "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  },
  sent_to_lab: {
    label: "Enviada al lab",
    className:
      "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800",
  },
  in_progress: {
    label: "En proceso",
    className:
      "bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-800",
  },
  ready: {
    label: "Lista",
    className:
      "bg-green-100 text-green-700 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-800",
  },
  delivered: {
    label: "Entregada",
    className:
      "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800",
  },
  cancelled: {
    label: "Cancelada",
    className:
      "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-800",
  },
};

const FALLBACK_CONFIG = {
  label: "Desconocido",
  className:
    "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300",
};

// ─── Component ────────────────────────────────────────────────────────────────

export function LabOrderStatusBadge({ status, className }: LabOrderStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? FALLBACK_CONFIG;

  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-medium border",
        config.className,
        className,
      )}
    >
      {config.label}
    </Badge>
  );
}
