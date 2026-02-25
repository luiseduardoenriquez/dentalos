"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ConditionBadgeProps {
  /** Condition code (e.g. "caries", "restoration") */
  code: string;
  /** Display label in Spanish */
  label: string;
  /** Hex color for the condition dot (e.g. "#D32F2F") */
  colorHex: string;
  /** Badge size variant */
  size?: "sm" | "md";
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Small color-coded badge showing a dental condition name with its color dot.
 * Uses inline style for the color dot since colors are dynamic hex values from the API.
 */
function ConditionBadge({
  code,
  label,
  colorHex,
  size = "sm",
  className,
}: ConditionBadgeProps) {
  return (
    <span
      data-condition={code}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--card))]",
        size === "sm" && "px-2 py-0.5 text-xs",
        size === "md" && "px-2.5 py-1 text-sm",
        className,
      )}
    >
      <span
        className={cn(
          "shrink-0 rounded-full",
          size === "sm" && "h-2 w-2",
          size === "md" && "h-2.5 w-2.5",
        )}
        style={{ backgroundColor: colorHex }}
        aria-hidden="true"
      />
      <span className="font-medium text-foreground">{label}</span>
    </span>
  );
}

ConditionBadge.displayName = "ConditionBadge";

export { ConditionBadge };
