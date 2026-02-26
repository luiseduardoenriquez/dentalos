"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConditionBadge } from "./condition-badge";
import type { CatalogCondition } from "@/lib/hooks/use-odontogram";
import {
  SEVERITIES,
  SEVERITY_LABELS,
  ZONE_LABELS,
  CONDITION_COLORS,
  CONDITION_LABELS,
} from "@/lib/validations/odontogram";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ConditionPanelProps {
  /** Full catalog of available dental conditions */
  conditions: CatalogCondition[];
  /** Currently selected condition code (null if none) */
  selectedCondition: string | null;
  /** Callback when a condition is selected from the palette */
  onConditionSelect: (conditionCode: string) => void;
  /** Currently selected zone — used to filter valid conditions */
  selectedZone: string | null;
  /** Currently selected severity */
  severity: string | null;
  /** Callback when severity changes */
  onSeverityChange: (severity: string | null) => void;
  /** Notes text */
  notes: string;
  /** Callback when notes change */
  onNotesChange: (notes: string) => void;
  /** Callback when the "Aplicar" (Apply) button is clicked */
  onApply: () => void;
  /** Whether the apply action is currently loading */
  isApplying?: boolean;
  /** Whether a zone is selected (enables/disables the panel) */
  hasSelection: boolean;
}

// ─── Fallback Conditions ─────────────────────────────────────────────────────

/**
 * Returns the default catalog conditions when the API catalog is not yet loaded.
 */
function getFallbackConditions(): CatalogCondition[] {
  return Object.entries(CONDITION_COLORS).map(([code, color]) => ({
    code,
    name_es: CONDITION_LABELS[code as keyof typeof CONDITION_LABELS] ?? code,
    name_en: code,
    color_hex: color,
    icon: "",
    zones: [],
    severity_applicable: ["caries", "fluorosis", "fracture"].includes(code),
  }));
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Condition palette panel for the odontogram.
 * Displays 12 dental conditions as a clickable grid with color indicators.
 * Shows severity selector and notes input when a condition is selected.
 */
function ConditionPanel({
  conditions,
  selectedCondition,
  onConditionSelect,
  selectedZone,
  severity,
  onSeverityChange,
  notes,
  onNotesChange,
  onApply,
  isApplying = false,
  hasSelection,
}: ConditionPanelProps) {
  // Use catalog conditions if available, fall back to static constants
  const displayConditions =
    conditions && conditions.length > 0 ? conditions : getFallbackConditions();

  // Filter conditions by zone validity (if the catalog provides zone info)
  const filteredConditions = selectedZone
    ? displayConditions.filter(
        (c) => c.zones.length === 0 || c.zones.includes(selectedZone),
      )
    : displayConditions;

  // Find the currently selected condition object
  const activeCondition = displayConditions.find(
    (c) => c.code === selectedCondition,
  );

  const showSeverity = activeCondition?.severity_applicable === true;

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">
          Condiciones dentales
        </CardTitle>
        {selectedZone ? (
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Zona seleccionada:{" "}
            <span className="font-medium text-foreground">
              {ZONE_LABELS[selectedZone as keyof typeof ZONE_LABELS] ?? selectedZone}
            </span>
          </p>
        ) : (
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Selecciona una zona del diente para aplicar una condicion.
          </p>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* ── Condition Grid ───────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-1.5">
          {filteredConditions.map((condition) => {
            const isActive = selectedCondition === condition.code;
            return (
              <button
                key={condition.code}
                type="button"
                onClick={() => onConditionSelect(condition.code)}
                disabled={!hasSelection}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2.5 py-2 text-left text-xs",
                  "transition-all duration-100 border",
                  isActive
                    ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                    : "border-transparent hover:bg-[hsl(var(--muted))]",
                  !hasSelection && "opacity-50 cursor-not-allowed",
                )}
                aria-pressed={isActive}
              >
                <span
                  className="h-3 w-3 shrink-0 rounded-full border border-black/10"
                  style={{ backgroundColor: condition.color_hex }}
                  aria-hidden="true"
                />
                <span
                  className={cn(
                    "font-medium truncate",
                    isActive ? "text-primary-700 dark:text-primary-300" : "text-foreground",
                  )}
                >
                  {condition.name_es}
                </span>
              </button>
            );
          })}
        </div>

        {/* ── Severity Selector ────────────────────────────────────────── */}
        {showSeverity && selectedCondition && hasSelection && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
              Severidad
            </p>
            <div className="flex gap-1.5">
              {SEVERITIES.map((sev) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() =>
                    onSeverityChange(severity === sev ? null : sev)
                  }
                  className={cn(
                    "rounded-md px-3 py-1.5 text-xs font-medium",
                    "transition-colors duration-100 border",
                    severity === sev
                      ? "border-primary-600 bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300"
                      : "border-[hsl(var(--border))] text-foreground hover:bg-[hsl(var(--muted))]",
                  )}
                  aria-pressed={severity === sev}
                >
                  {SEVERITY_LABELS[sev]}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Notes Input ──────────────────────────────────────────────── */}
        {selectedCondition && hasSelection && (
          <div className="space-y-2">
            <label
              htmlFor="condition-notes"
              className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
            >
              Notas (opcional)
            </label>
            <textarea
              id="condition-notes"
              value={notes}
              onChange={(e) => onNotesChange(e.target.value)}
              maxLength={500}
              rows={2}
              placeholder="Observaciones adicionales..."
              className={cn(
                "w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                "px-3 py-2 text-sm text-foreground resize-none",
                "placeholder:text-[hsl(var(--muted-foreground))]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
              )}
            />
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] text-right">
              {notes.length}/500
            </p>
          </div>
        )}

        {/* ── Selected Condition Preview ────────────────────────────────── */}
        {activeCondition && hasSelection && (
          <div className="flex items-center gap-2 rounded-md bg-[hsl(var(--muted))] px-3 py-2">
            <ConditionBadge
              code={activeCondition.code}
              label={activeCondition.name_es}
              colorHex={activeCondition.color_hex}
              size="md"
            />
            {severity && (
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                ({SEVERITY_LABELS[severity as keyof typeof SEVERITY_LABELS]})
              </span>
            )}
          </div>
        )}

        {/* ── Apply Button ─────────────────────────────────────────────── */}
        <Button
          onClick={onApply}
          disabled={!hasSelection || !selectedCondition || isApplying}
          className="w-full"
          size="sm"
        >
          {isApplying ? "Aplicando..." : "Aplicar"}
        </Button>
      </CardContent>
    </Card>
  );
}

ConditionPanel.displayName = "ConditionPanel";

export { ConditionPanel };
