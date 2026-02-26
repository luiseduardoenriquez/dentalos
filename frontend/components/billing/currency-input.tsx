"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface CurrencyInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> {
  /** Value in cents (integer) */
  value: number | undefined;
  /** Called with value in cents */
  onChange: (cents: number) => void;
  currency?: string;
}

/**
 * Currency input that displays whole COP units and converts to/from cents.
 * E.g. user types "150000" → onChange receives 15000000 (cents)
 */
export function CurrencyInput({
  value,
  onChange,
  currency = "COP",
  className,
  ...props
}: CurrencyInputProps) {
  const displayValue = value !== undefined ? Math.round(value / 100) : "";

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value.replace(/[^0-9]/g, "");
    if (raw === "") {
      onChange(0);
      return;
    }
    const wholeUnits = parseInt(raw, 10);
    onChange(wholeUnits * 100);
  }

  return (
    <div className="relative">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[hsl(var(--muted-foreground))] pointer-events-none">
        $
      </span>
      <Input
        type="text"
        inputMode="numeric"
        value={displayValue}
        onChange={handleChange}
        className={cn("pl-7 tabular-nums", className)}
        {...props}
      />
    </div>
  );
}
