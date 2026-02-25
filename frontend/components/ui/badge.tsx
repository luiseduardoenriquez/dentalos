"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// ─── Variants ─────────────────────────────────────────────────────────────────

const badgeVariants = cva(
  [
    "inline-flex items-center rounded-full px-2.5 py-0.5",
    "text-xs font-semibold",
    "transition-colors",
    "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-2",
  ],
  {
    variants: {
      variant: {
        default: [
          "bg-primary-100 text-primary-700 border border-primary-200",
          "dark:bg-primary-900/30 dark:text-primary-300 dark:border-primary-700/40",
        ],
        secondary: [
          "bg-secondary-100 text-secondary-700 border border-secondary-200",
          "dark:bg-secondary-900/30 dark:text-secondary-300 dark:border-secondary-700/40",
        ],
        outline: [
          "bg-transparent text-foreground border border-[hsl(var(--border))]",
        ],
        destructive: [
          "bg-destructive-100 text-destructive-700 border border-destructive-200",
          "dark:bg-destructive-900/30 dark:text-destructive-300 dark:border-destructive-700/40",
        ],
        success: [
          "bg-success-50 text-success-700 border border-success-500/30",
          "dark:bg-success-700/20 dark:text-success-300 dark:border-success-500/40",
        ],
        warning: [
          "bg-warning-50 text-accent-700 border border-accent-500/30",
          "dark:bg-accent-700/20 dark:text-accent-300 dark:border-accent-500/40",
        ],
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

// ─── Component ────────────────────────────────────────────────────────────────

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
