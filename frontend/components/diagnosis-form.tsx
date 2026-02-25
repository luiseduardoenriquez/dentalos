"use client";

import * as React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CatalogSearch } from "@/components/catalog-search";
import {
  diagnosisCreateSchema,
  SEVERITY_OPTIONS,
  SEVERITY_LABELS,
  type DiagnosisCreate,
} from "@/lib/validations/diagnosis";
import { useCreateDiagnosis, useUpdateDiagnosis, type DiagnosisResponse } from "@/lib/hooks/use-diagnoses";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DiagnosisFormProps {
  patientId: string;
  onSuccess?: () => void;
  initialData?: DiagnosisResponse;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Form for creating or editing a patient diagnosis.
 *
 * - Uses CatalogSearch for CIE-10 code lookup with debounced autocomplete.
 * - Severity select with Spanish labels.
 * - Optional FDI tooth number input (11–85).
 * - Optional clinical notes textarea.
 * - Submit shows spinner while in-flight, calls onSuccess when done.
 *
 * @example
 * <DiagnosisForm patientId={patient.id} onSuccess={() => setOpen(false)} />
 */
export function DiagnosisForm({ patientId, onSuccess, initialData }: DiagnosisFormProps) {
  const isEditing = Boolean(initialData);

  const createDiagnosis = useCreateDiagnosis(patientId);
  const updateDiagnosis = useUpdateDiagnosis(patientId);

  const isPending = createDiagnosis.isPending || updateDiagnosis.isPending;

  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors },
  } = useForm<DiagnosisCreate>({
    resolver: zodResolver(diagnosisCreateSchema),
    defaultValues: {
      cie10_code: initialData?.cie10_code ?? "",
      cie10_description: initialData?.cie10_description ?? "",
      severity: (initialData?.severity as DiagnosisCreate["severity"]) ?? "mild",
      tooth_number: initialData?.tooth_number ?? null,
      notes: initialData?.notes ?? null,
    },
  });

  const cie10Code = watch("cie10_code");
  const cie10Description = watch("cie10_description");

  function handleCatalogSelect(code: string, description: string) {
    setValue("cie10_code", code, { shouldValidate: true });
    setValue("cie10_description", description, { shouldValidate: true });
  }

  function onSubmit(data: DiagnosisCreate) {
    if (isEditing && initialData) {
      updateDiagnosis.mutate(
        { diagnosisId: initialData.id, data: { severity: data.severity, notes: data.notes } },
        { onSuccess },
      );
    } else {
      createDiagnosis.mutate(data, { onSuccess });
    }
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <CardTitle className="text-base font-semibold">
          {isEditing ? "Editar diagnóstico" : "Nuevo diagnóstico"}
        </CardTitle>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">

          {/* CIE-10 Code + Description */}
          <div className="space-y-1.5">
            <Label htmlFor="cie10_code" className="text-sm font-medium">
              Código CIE-10 <span className="text-destructive-500" aria-hidden>*</span>
            </Label>
            <CatalogSearch
              type="cie10"
              value={cie10Code ? `${cie10Code} — ${cie10Description}` : ""}
              onSelect={handleCatalogSelect}
              placeholder="Buscar diagnóstico CIE-10 (ej: K02, caries...)"
              disabled={isEditing}
            />
            {/* Hidden inputs to hold the validated values */}
            <input type="hidden" {...register("cie10_code")} />
            <input type="hidden" {...register("cie10_description")} />
            {errors.cie10_code && (
              <p className="text-xs text-destructive-600 mt-1" role="alert">
                {errors.cie10_code.message}
              </p>
            )}
            {errors.cie10_description && !errors.cie10_code && (
              <p className="text-xs text-destructive-600 mt-1" role="alert">
                {errors.cie10_description.message}
              </p>
            )}
          </div>

          {/* Severity */}
          <div className="space-y-1.5">
            <Label htmlFor="severity" className="text-sm font-medium">
              Severidad <span className="text-destructive-500" aria-hidden>*</span>
            </Label>
            <Controller
              name="severity"
              control={control}
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={isPending}
                >
                  <SelectTrigger id="severity" aria-describedby={errors.severity ? "severity-error" : undefined}>
                    <SelectValue placeholder="Selecciona la severidad" />
                  </SelectTrigger>
                  <SelectContent>
                    {SEVERITY_OPTIONS.map((option) => (
                      <SelectItem key={option} value={option}>
                        {SEVERITY_LABELS[option]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.severity && (
              <p id="severity-error" className="text-xs text-destructive-600 mt-1" role="alert">
                {errors.severity.message}
              </p>
            )}
          </div>

          {/* Tooth Number (optional) */}
          <div className="space-y-1.5">
            <Label htmlFor="tooth_number" className="text-sm font-medium">
              Diente (FDI)
              <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))] font-normal">
                opcional
              </span>
            </Label>
            <input
              id="tooth_number"
              type="number"
              min={11}
              max={85}
              placeholder="ej: 16, 21, 36..."
              disabled={isPending}
              aria-describedby={errors.tooth_number ? "tooth-error" : undefined}
              {...register("tooth_number", {
                setValueAs: (v) => (v === "" ? null : Number(v)),
              })}
              className={cn(
                "w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                "px-3 py-2 text-sm",
                "placeholder:text-[hsl(var(--muted-foreground))]",
                "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                "disabled:cursor-not-allowed disabled:opacity-50",
                "transition-colors duration-150",
                errors.tooth_number && "border-destructive-500 focus:ring-destructive-500",
              )}
            />
            {errors.tooth_number && (
              <p id="tooth-error" className="text-xs text-destructive-600 mt-1" role="alert">
                {errors.tooth_number.message}
              </p>
            )}
          </div>

          {/* Notes (optional) */}
          <div className="space-y-1.5">
            <Label htmlFor="notes" className="text-sm font-medium">
              Notas clínicas
              <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))] font-normal">
                opcional
              </span>
            </Label>
            <textarea
              id="notes"
              rows={3}
              placeholder="Observaciones adicionales sobre el diagnóstico..."
              disabled={isPending}
              aria-describedby={errors.notes ? "notes-error" : undefined}
              {...register("notes")}
              className={cn(
                "w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                "px-3 py-2 text-sm",
                "placeholder:text-[hsl(var(--muted-foreground))]",
                "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                "disabled:cursor-not-allowed disabled:opacity-50",
                "resize-none transition-colors duration-150",
                errors.notes && "border-destructive-500 focus:ring-destructive-500",
              )}
            />
            {errors.notes && (
              <p id="notes-error" className="text-xs text-destructive-600 mt-1" role="alert">
                {errors.notes.message}
              </p>
            )}
          </div>

          {/* Submit */}
          <div className="flex justify-end pt-2">
            <Button type="submit" disabled={isPending} className="min-w-[140px]">
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : isEditing ? (
                "Actualizar diagnóstico"
              ) : (
                "Crear diagnóstico"
              )}
            </Button>
          </div>

        </form>
      </CardContent>
    </Card>
  );
}
