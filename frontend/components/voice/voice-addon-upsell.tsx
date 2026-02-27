"use client";

import { Mic, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface VoiceAddonUpsellProps {
  /** Variant: "inline" renders a compact banner, "popover" renders for use in a popover/modal */
  variant?: "inline" | "popover";
  className?: string;
}

/**
 * Upsell notice for the voice dictation add-on.
 * Shown when the tenant's plan does not include voice_dictation feature.
 */
export function VoiceAddonUpsell({ variant = "inline", className }: VoiceAddonUpsellProps) {
  if (variant === "popover") {
    return (
      <div className={cn("space-y-3 p-4 max-w-xs", className)}>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/30">
            <Mic className="h-4 w-4 text-primary-600" />
          </div>
          <p className="text-sm font-medium text-foreground">Dictado por Voz</p>
        </div>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Dicte hallazgos clinicos y apliquelos al odontograma automaticamente.
          Hasta 5x mas rapido que el ingreso manual.
        </p>
        <div className="flex items-center gap-1 text-xs text-primary-600">
          <Sparkles className="h-3 w-3" />
          <span>$10 USD / doctor / mes</span>
        </div>
        <Button size="sm" className="w-full" asChild>
          <a href="/settings/billing">Activar complemento</a>
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border border-primary-200 bg-primary-50 px-3 py-2",
        "dark:border-primary-800 dark:bg-primary-900/20",
        className,
      )}
    >
      <Mic className="h-4 w-4 shrink-0 text-primary-600" />
      <p className="text-xs text-primary-700 dark:text-primary-300">
        <span className="font-medium">Dictado por Voz</span> no esta incluido en su plan.{" "}
        <a
          href="/settings/billing"
          className="underline hover:text-primary-900 dark:hover:text-primary-100"
        >
          Activar por $10/doctor/mes
        </a>
      </p>
    </div>
  );
}
