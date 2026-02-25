"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Skeleton loading placeholder.
 * Use className to control dimensions: "h-4 w-32" for a text line, "h-10 w-full" for input, etc.
 */
function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[hsl(var(--muted))]",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
