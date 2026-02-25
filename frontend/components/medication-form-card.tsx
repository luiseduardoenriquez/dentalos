"use client";

import * as React from "react";
import { X } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { VIA_OPTIONS, VIA_LABELS } from "@/lib/validations/prescription";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MedicationFormCardProps {
  /** 0-based index of this medication in the list */
  index: number;
  medication: {
    name: string;
    dosis: string;
    frecuencia: string;
    duracion_dias: number;
    via: string;
    instrucciones: string | null;
  };
  onChange: (index: number, field: string, value: string | number) => void;
  onRemove: (index: number) => void;
  /** Field-level error messages keyed by field name */
  errors?: Record<string, string>;
}

// ─── Field Error ──────────────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p className="mt-1 text-xs text-destructive-600 dark:text-destructive-400" role="alert">
      {message}
    </p>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function MedicationFormCard({
  index,
  medication,
  onChange,
  onRemove,
  errors = {},
}: MedicationFormCardProps) {
  return (
    <Card
      className={cn(
        "relative border",
        Object.keys(errors).length > 0 && "border-destructive-400",
      )}
    >
      {/* ─── Card Header ──────────────────────────────────────────────────── */}
      <CardHeader className="pb-3 pt-4 px-4 flex flex-row items-center justify-between">
        <span className="text-sm font-semibold text-foreground">
          Medicamento #{index + 1}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => onRemove(index)}
          className="h-7 w-7 text-[hsl(var(--muted-foreground))] hover:text-destructive-600"
          aria-label={`Eliminar medicamento ${index + 1}`}
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      {/* ─── Card Content ─────────────────────────────────────────────────── */}
      <CardContent className="px-4 pb-4 space-y-3">
        {/* Nombre del medicamento — full width */}
        <div className="space-y-1">
          <Label htmlFor={`med-${index}-name`}>
            Nombre del medicamento <span className="text-destructive-600">*</span>
          </Label>
          <Input
            id={`med-${index}-name`}
            placeholder="Ej: Amoxicilina 500mg"
            value={medication.name}
            onChange={(e) => onChange(index, "name", e.target.value)}
            aria-invalid={Boolean(errors.name)}
          />
          <FieldError message={errors.name} />
        </div>

        {/* Dosis + Frecuencia — side by side */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <Label htmlFor={`med-${index}-dosis`}>
              Dosis <span className="text-destructive-600">*</span>
            </Label>
            <Input
              id={`med-${index}-dosis`}
              placeholder="Ej: 500mg"
              value={medication.dosis}
              onChange={(e) => onChange(index, "dosis", e.target.value)}
              aria-invalid={Boolean(errors.dosis)}
            />
            <FieldError message={errors.dosis} />
          </div>

          <div className="space-y-1">
            <Label htmlFor={`med-${index}-frecuencia`}>
              Frecuencia <span className="text-destructive-600">*</span>
            </Label>
            <Input
              id={`med-${index}-frecuencia`}
              placeholder="Ej: Cada 8 horas"
              value={medication.frecuencia}
              onChange={(e) => onChange(index, "frecuencia", e.target.value)}
              aria-invalid={Boolean(errors.frecuencia)}
            />
            <FieldError message={errors.frecuencia} />
          </div>
        </div>

        {/* Duración (días) + Vía — side by side */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <Label htmlFor={`med-${index}-duracion_dias`}>
              Duración (días) <span className="text-destructive-600">*</span>
            </Label>
            <Input
              id={`med-${index}-duracion_dias`}
              type="number"
              min={1}
              max={365}
              placeholder="Ej: 7"
              value={medication.duracion_dias === 0 ? "" : medication.duracion_dias}
              onChange={(e) =>
                onChange(index, "duracion_dias", e.target.value === "" ? 0 : Number(e.target.value))
              }
              aria-invalid={Boolean(errors.duracion_dias)}
            />
            <FieldError message={errors.duracion_dias} />
          </div>

          <div className="space-y-1">
            <Label htmlFor={`med-${index}-via`}>Vía de administración</Label>
            <Select
              value={medication.via || "oral"}
              onValueChange={(val) => onChange(index, "via", val)}
            >
              <SelectTrigger id={`med-${index}-via`} aria-label="Vía de administración">
                <SelectValue placeholder="Selecciona vía" />
              </SelectTrigger>
              <SelectContent>
                {VIA_OPTIONS.map((via) => (
                  <SelectItem key={via} value={via}>
                    {VIA_LABELS[via]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FieldError message={errors.via} />
          </div>
        </div>

        {/* Instrucciones — full width, optional */}
        <div className="space-y-1">
          <Label htmlFor={`med-${index}-instrucciones`}>
            Instrucciones adicionales{" "}
            <span className="text-xs text-[hsl(var(--muted-foreground))] font-normal">
              (opcional)
            </span>
          </Label>
          <textarea
            id={`med-${index}-instrucciones`}
            rows={2}
            placeholder="Ej: Tomar con alimentos, evitar alcohol..."
            value={medication.instrucciones ?? ""}
            onChange={(e) =>
              onChange(index, "instrucciones", e.target.value || "")
            }
            className="flex w-full rounded-md border border-[hsl(var(--input))] bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-600 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
            aria-invalid={Boolean(errors.instrucciones)}
          />
          <FieldError message={errors.instrucciones} />
        </div>
      </CardContent>
    </Card>
  );
}
