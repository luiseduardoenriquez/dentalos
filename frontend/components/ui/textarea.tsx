"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Styled textarea input following DentalOS design tokens.
 * Drop-in replacement for shadcn/ui Textarea.
 */
const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "flex w-full rounded-md border border-[hsl(var(--border))]",
          "bg-[hsl(var(--background))] px-3 py-2",
          "text-sm text-foreground placeholder:text-[hsl(var(--muted-foreground))]",
          "shadow-sm transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "read-only:bg-[hsl(var(--muted))] read-only:cursor-default",
          className,
        )}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

export { Textarea };
