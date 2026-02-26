"use client";

import * as React from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { CatalogSearch } from "@/components/catalog-search";
import { procedureCreateSchema, type ProcedureCreate } from "@/lib/validations/procedure";
import { useCreateProcedure } from "@/lib/hooks/use-procedures";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ProcedureFormProps {
  patientId: string;
  onSuccess?: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Form for recording a new clinical procedure for a patient.
 *
 * - Uses CatalogSearch for CUPS code lookup with debounced autocomplete.
 * - Optional FDI tooth number input (11–85).
 * - Dynamic zones checklist input (free-text tags).
 * - Dynamic materials used list (name + optional quantity).
 * - Optional links to treatment plan item and clinical record.
 * - Duration in minutes.
 *
 * @example
 * <ProcedureForm patientId={patient.id} onSuccess={() => setOpen(false)} />
 */
export function ProcedureForm({ patientId, onSuccess }: ProcedureFormProps) {
  const createProcedure = useCreateProcedure(patientId);
  const isPending = createProcedure.isPending;

  const [zoneInput, setZoneInput] = React.useState("");

  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ProcedureCreate>({
    resolver: zodResolver(procedureCreateSchema),
    defaultValues: {
      cups_code: "",
      cups_description: "",
      tooth_number: null,
      zones: [],
      materials_used: [],
      treatment_plan_item_id: null,
      clinical_record_id: null,
      duration_minutes: null,
    },
  });

  const { fields: materialFields, append: appendMaterial, remove: removeMaterial } = useFieldArray({
    control,
    name: "materials_used",
  });

  const cupsCode = watch("cups_code");
  const cupsDescription = watch("cups_description");
  const zones = watch("zones") ?? [];

  function handleCatalogSelect(code: string, description: string) {
    setValue("cups_code", code, { shouldValidate: true });
    setValue("cups_description", description, { shouldValidate: true });
  }

  function handleAddZone() {
    const trimmed = zoneInput.trim();
    if (!trimmed || zones.includes(trimmed)) return;
    setValue("zones", [...zones, trimmed]);
    setZoneInput("");
  }

  function handleRemoveZone(zone: string) {
    setValue("zones", zones.filter((z) => z !== zone));
  }

  function handleZoneKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddZone();
    }
  }

  function onSubmit(data: ProcedureCreate) {
    createProcedure.mutate(data, { onSuccess });
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <CardTitle className="text-base font-semibold">Nuevo procedimiento</CardTitle>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">

          {/* CUPS Code + Description */}
          <div className="space-y-1.5">
            <Label htmlFor="cups_code" className="text-sm font-medium">
              Código CUPS <span className="text-destructive-500" aria-hidden>*</span>
            </Label>
            <CatalogSearch
              type="cups"
              value={cupsCode ? `${cupsCode} — ${cupsDescription}` : ""}
              onSelect={handleCatalogSelect}
              placeholder="Buscar procedimiento CUPS (ej: 890302...)"
            />
            <input type="hidden" {...register("cups_code")} />
            <input type="hidden" {...register("cups_description")} />
            {errors.cups_code && (
              <p className="text-xs text-destructive-600 mt-1" role="alert">
                {errors.cups_code.message}
              </p>
            )}
            {errors.cups_description && !errors.cups_code && (
              <p className="text-xs text-destructive-600 mt-1" role="alert">
                {errors.cups_description.message}
              </p>
            )}
          </div>

          {/* Tooth Number + Duration — 2-column row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Tooth Number */}
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
                placeholder="ej: 16, 21..."
                disabled={isPending}
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
                  errors.tooth_number && "border-destructive-500",
                )}
              />
              {errors.tooth_number && (
                <p className="text-xs text-destructive-600 mt-1" role="alert">
                  {errors.tooth_number.message}
                </p>
              )}
            </div>

            {/* Duration */}
            <div className="space-y-1.5">
              <Label htmlFor="duration_minutes" className="text-sm font-medium">
                Duración (min)
                <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))] font-normal">
                  opcional
                </span>
              </Label>
              <input
                id="duration_minutes"
                type="number"
                min={1}
                max={480}
                placeholder="ej: 30, 60..."
                disabled={isPending}
                {...register("duration_minutes", {
                  setValueAs: (v) => (v === "" ? null : Number(v)),
                })}
                className={cn(
                  "w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                  "px-3 py-2 text-sm",
                  "placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                  "transition-colors duration-150",
                  errors.duration_minutes && "border-destructive-500",
                )}
              />
              {errors.duration_minutes && (
                <p className="text-xs text-destructive-600 mt-1" role="alert">
                  {errors.duration_minutes.message}
                </p>
              )}
            </div>
          </div>

          {/* Zones */}
          <div className="space-y-1.5">
            <Label className="text-sm font-medium">
              Zonas
              <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))] font-normal">
                opcional
              </span>
            </Label>
            <div className="flex gap-2">
              <input
                type="text"
                value={zoneInput}
                onChange={(e) => setZoneInput(e.target.value)}
                onKeyDown={handleZoneKeyDown}
                placeholder="ej: mesial, oclusal... (Enter para agregar)"
                disabled={isPending}
                className={cn(
                  "flex-1 rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                  "px-3 py-2 text-sm",
                  "placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                  "transition-colors duration-150",
                )}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddZone}
                disabled={!zoneInput.trim() || isPending}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {zones.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {zones.map((zone) => (
                  <span
                    key={zone}
                    className="inline-flex items-center gap-1 rounded-full bg-primary-100 dark:bg-primary-900/30 px-2.5 py-0.5 text-xs font-medium text-primary-700 dark:text-primary-300"
                  >
                    {zone}
                    <button
                      type="button"
                      onClick={() => handleRemoveZone(zone)}
                      aria-label={`Eliminar zona ${zone}`}
                      className="ml-0.5 hover:text-primary-900 transition-colors"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Materials Used */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">
                Materiales utilizados
                <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))] font-normal">
                  opcional
                </span>
              </Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => appendMaterial({ name: "", quantity: undefined })}
                disabled={isPending}
                className="h-7 text-xs"
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Agregar material
              </Button>
            </div>

            {materialFields.length > 0 && (
              <div className="space-y-2">
                {materialFields.map((field, idx) => (
                  <div key={field.id} className="flex gap-2 items-start">
                    <input
                      type="text"
                      placeholder="Nombre del material"
                      disabled={isPending}
                      {...register(`materials_used.${idx}.name` as const)}
                      className={cn(
                        "flex-1 rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                        "px-3 py-2 text-sm",
                        "placeholder:text-[hsl(var(--muted-foreground))]",
                        "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                        "disabled:cursor-not-allowed disabled:opacity-50",
                        "transition-colors duration-150",
                      )}
                    />
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      placeholder="Cant."
                      disabled={isPending}
                      {...register(`materials_used.${idx}.quantity` as const, {
                        setValueAs: (v) => (v === "" ? undefined : Number(v)),
                      })}
                      className={cn(
                        "w-20 rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                        "px-3 py-2 text-sm",
                        "placeholder:text-[hsl(var(--muted-foreground))]",
                        "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                        "disabled:cursor-not-allowed disabled:opacity-50",
                        "transition-colors duration-150",
                      )}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeMaterial(idx)}
                      disabled={isPending}
                      aria-label="Eliminar material"
                      className="h-9 w-9 p-0 text-[hsl(var(--muted-foreground))] hover:text-destructive-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Optional links */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Treatment Plan Item ID */}
            <div className="space-y-1.5">
              <Label htmlFor="treatment_plan_item_id" className="text-sm font-medium">
                Ítem de plan de tratamiento
                <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))] font-normal">
                  opcional
                </span>
              </Label>
              <input
                id="treatment_plan_item_id"
                type="text"
                placeholder="UUID del ítem"
                disabled={isPending}
                {...register("treatment_plan_item_id")}
                className={cn(
                  "w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                  "px-3 py-2 text-sm font-mono",
                  "placeholder:text-[hsl(var(--muted-foreground))] placeholder:font-sans",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                  "transition-colors duration-150",
                  errors.treatment_plan_item_id && "border-destructive-500",
                )}
              />
              {errors.treatment_plan_item_id && (
                <p className="text-xs text-destructive-600 mt-1" role="alert">
                  {errors.treatment_plan_item_id.message}
                </p>
              )}
            </div>

            {/* Clinical Record ID */}
            <div className="space-y-1.5">
              <Label htmlFor="clinical_record_id" className="text-sm font-medium">
                Registro clínico
                <span className="ml-1.5 text-xs text-[hsl(var(--muted-foreground))] font-normal">
                  opcional
                </span>
              </Label>
              <input
                id="clinical_record_id"
                type="text"
                placeholder="UUID del registro"
                disabled={isPending}
                {...register("clinical_record_id")}
                className={cn(
                  "w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                  "px-3 py-2 text-sm font-mono",
                  "placeholder:text-[hsl(var(--muted-foreground))] placeholder:font-sans",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                  "transition-colors duration-150",
                  errors.clinical_record_id && "border-destructive-500",
                )}
              />
              {errors.clinical_record_id && (
                <p className="text-xs text-destructive-600 mt-1" role="alert">
                  {errors.clinical_record_id.message}
                </p>
              )}
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-end pt-2">
            <Button type="submit" disabled={isPending} className="min-w-[160px]">
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                "Registrar procedimiento"
              )}
            </Button>
          </div>

        </form>
      </CardContent>
    </Card>
  );
}
