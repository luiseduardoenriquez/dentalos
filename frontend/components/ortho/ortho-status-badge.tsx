"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ORTHO_STATUS_LABELS } from "@/lib/validations/ortho";

// ─── Status Variant Map ───────────────────────────────────────────────────────

const STATUS_VARIANTS: Record<string, string> = {
  planning:
    "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
  bonding:
    "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-700",
  active_treatment:
    "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
  retention:
    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-700",
  completed:
    "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
  cancelled:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Color-coded badge for an orthodontic case status.
 * Maps each status to a tailwind color class and a Spanish label.
 */
export function OrthoStatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", STATUS_VARIANTS[status] ?? "")}
    >
      {ORTHO_STATUS_LABELS[status] ?? status}
    </Badge>
  );
}
