"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Optional start adornment (icon) rendered inside the input on the left */
  startAdornment?: React.ReactNode;
  /** Optional end adornment (icon or button) rendered inside the input on the right */
  endAdornment?: React.ReactNode;
}

// ─── Component ────────────────────────────────────────────────────────────────

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, startAdornment, endAdornment, ...props }, ref) => {
    if (startAdornment || endAdornment) {
      return (
        <div className="relative flex items-center">
          {startAdornment && (
            <div className="pointer-events-none absolute left-3 flex items-center text-[hsl(var(--muted-foreground))]">
              {startAdornment}
            </div>
          )}
          <input
            ref={ref}
            type={type}
            className={cn(
              "flex h-10 w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
              "px-3 py-2 text-sm text-foreground",
              "placeholder:text-[hsl(var(--muted-foreground))]",
              "transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-0",
              "disabled:cursor-not-allowed disabled:opacity-50",
              "aria-invalid:border-destructive-500 aria-invalid:ring-destructive-500",
              "dark:border-[hsl(var(--input))] dark:bg-[hsl(var(--background))]",
              startAdornment && "pl-9",
              endAdornment && "pr-9",
              className,
            )}
            {...props}
          />
          {endAdornment && (
            <div className="absolute right-3 flex items-center text-[hsl(var(--muted-foreground))]">
              {endAdornment}
            </div>
          )}
        </div>
      );
    }

    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
          "px-3 py-2 text-sm text-foreground",
          "placeholder:text-[hsl(var(--muted-foreground))]",
          "transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-0",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "aria-invalid:border-destructive-500 aria-invalid:ring-destructive-500",
          "dark:border-[hsl(var(--input))] dark:bg-[hsl(var(--background))]",
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
