"use client";

import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface LabelProps
  extends React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> {
  /** Renders a red asterisk (*) after the label text to indicate required field */
  required?: boolean;
  /** Applies error styling (red color) */
  error?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  LabelProps
>(({ className, required, error, children, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(
      "text-sm font-medium leading-none",
      "peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
      error
        ? "text-destructive-600 dark:text-destructive-400"
        : "text-foreground",
      className,
    )}
    {...props}
  >
    {children}
    {required && (
      <span
        className="ml-0.5 text-destructive-600 dark:text-destructive-400"
        aria-hidden="true"
      >
        *
      </span>
    )}
  </LabelPrimitive.Root>
));
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
