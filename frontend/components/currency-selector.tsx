"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type SupportedCurrency = "COP" | "USD" | "EUR" | "MXN";

export interface CurrencySelectorProps {
  value: SupportedCurrency;
  onChange: (currency: SupportedCurrency) => void;
  className?: string;
  disabled?: boolean;
  size?: "sm" | "default";
}

// ─── Currency config ──────────────────────────────────────────────────────────

const CURRENCIES: {
  code: SupportedCurrency;
  label: string;
  flag: string;
  symbol: string;
}[] = [
  { code: "COP", label: "Peso colombiano", flag: "🇨🇴", symbol: "$" },
  { code: "USD", label: "Dólar estadounidense", flag: "🇺🇸", symbol: "US$" },
  { code: "EUR", label: "Euro", flag: "🇪🇺", symbol: "€" },
  { code: "MXN", label: "Peso mexicano", flag: "🇲🇽", symbol: "MX$" },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function CurrencySelector({
  value,
  onChange,
  className,
  disabled,
  size = "default",
}: CurrencySelectorProps) {
  const selected = CURRENCIES.find((c) => c.code === value) ?? CURRENCIES[0];

  return (
    <div className={cn("relative inline-block", className)}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as SupportedCurrency)}
        disabled={disabled}
        aria-label="Seleccionar moneda"
        className={cn(
          "appearance-none rounded-md border border-[hsl(var(--border))]",
          "bg-[hsl(var(--background))] text-foreground",
          "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent",
          "pr-8 pl-3 transition-colors",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          size === "sm"
            ? "py-1 text-xs h-7"
            : "py-2 text-sm h-9",
        )}
      >
        {CURRENCIES.map((c) => (
          <option key={c.code} value={c.code}>
            {c.flag} {c.code} — {c.label}
          </option>
        ))}
      </select>

      {/* Custom dropdown arrow overlay */}
      <div className="pointer-events-none absolute inset-y-0 right-2 flex items-center">
        <svg
          className="h-4 w-4 text-[hsl(var(--muted-foreground))]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Accessible label for screen readers */}
      <span className="sr-only">
        Moneda seleccionada: {selected.label} ({selected.code})
      </span>
    </div>
  );
}
