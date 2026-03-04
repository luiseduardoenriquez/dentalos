"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { LabOrderCreate, DentalLabResponse } from "@/lib/hooks/use-lab-orders";

// ─── Validation Schema ────────────────────────────────────────────────────────

const labOrderSchema = z.object({
  patient_id: z.string().min(1, "El ID del paciente es requerido"),
  order_type: z.string().min(1, "El tipo de orden es requerido"),
  treatment_plan_id: z.string().optional().nullable(),
  lab_id: z.string().optional().nullable(),
  specifications: z.string().optional().nullable(),
  due_date: z.string().optional().nullable(),
  cost_cents: z.coerce.number().int().min(0).optional().nullable(),
  notes: z.string().optional().nullable(),
});

type LabOrderFormValues = z.infer<typeof labOrderSchema>;

// ─── Constants ────────────────────────────────────────────────────────────────

const ORDER_TYPES = [
  { value: "corona", label: "Corona" },
  { value: "puente", label: "Puente" },
  { value: "protesis", label: "Prótesis" },
  { value: "abutment_implante", label: "Abutment implante" },
  { value: "retenedor", label: "Retenedor" },
  { value: "otro", label: "Otro" },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface LabOrderFormProps {
  onSubmit: (data: LabOrderCreate) => void;
  isLoading: boolean;
  labs: DentalLabResponse[];
  defaultValues?: Partial<LabOrderCreate>;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function LabOrderForm({
  onSubmit,
  isLoading,
  labs,
  defaultValues,
}: LabOrderFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<LabOrderFormValues>({
    resolver: zodResolver(labOrderSchema),
    defaultValues: {
      patient_id: defaultValues?.patient_id ?? "",
      order_type: defaultValues?.order_type ?? "",
      treatment_plan_id: defaultValues?.treatment_plan_id ?? null,
      lab_id: defaultValues?.lab_id ?? null,
      specifications: defaultValues?.specifications ?? null,
      due_date: defaultValues?.due_date ?? null,
      cost_cents: defaultValues?.cost_cents ?? null,
      notes: defaultValues?.notes ?? null,
    },
  });

  const selectedOrderType = watch("order_type");
  const selectedLabId = watch("lab_id");

  function handleFormSubmit(values: LabOrderFormValues) {
    onSubmit({
      patient_id: values.patient_id,
      order_type: values.order_type,
      treatment_plan_id: values.treatment_plan_id || null,
      lab_id: values.lab_id || null,
      specifications: values.specifications || null,
      due_date: values.due_date || null,
      cost_cents: values.cost_cents ?? null,
      notes: values.notes || null,
    });
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-5">
      {/* patient_id */}
      <div className="space-y-1.5">
        <Label htmlFor="patient_id">
          ID del paciente <span className="text-red-500">*</span>
        </Label>
        <Input
          id="patient_id"
          placeholder="UUID del paciente"
          {...register("patient_id")}
          className={cn(errors.patient_id && "border-red-500")}
        />
        {errors.patient_id && (
          <p className="text-xs text-red-600">{errors.patient_id.message}</p>
        )}
      </div>

      {/* treatment_plan_id */}
      <div className="space-y-1.5">
        <Label htmlFor="treatment_plan_id">ID del plan de tratamiento (opcional)</Label>
        <Input
          id="treatment_plan_id"
          placeholder="UUID del plan de tratamiento"
          {...register("treatment_plan_id")}
        />
      </div>

      {/* lab_id */}
      <div className="space-y-1.5">
        <Label htmlFor="lab_id">Laboratorio</Label>
        <Select
          value={selectedLabId ?? "none"}
          onValueChange={(v) => setValue("lab_id", v === "none" ? null : v)}
        >
          <SelectTrigger id="lab_id">
            <SelectValue placeholder="Seleccionar laboratorio" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Sin laboratorio asignado</SelectItem>
            {labs.map((lab) => (
              <SelectItem key={lab.id} value={lab.id}>
                {lab.name}
                {lab.city ? ` — ${lab.city}` : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* order_type */}
      <div className="space-y-1.5">
        <Label htmlFor="order_type">
          Tipo de orden <span className="text-red-500">*</span>
        </Label>
        <Select
          value={selectedOrderType ?? ""}
          onValueChange={(v) => setValue("order_type", v)}
        >
          <SelectTrigger
            id="order_type"
            className={cn(errors.order_type && "border-red-500")}
          >
            <SelectValue placeholder="Seleccionar tipo" />
          </SelectTrigger>
          <SelectContent>
            {ORDER_TYPES.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errors.order_type && (
          <p className="text-xs text-red-600">{errors.order_type.message}</p>
        )}
      </div>

      {/* specifications */}
      <div className="space-y-1.5">
        <Label htmlFor="specifications">Especificaciones</Label>
        <Textarea
          id="specifications"
          placeholder="Detalles técnicos, materiales, color, indicaciones especiales..."
          rows={4}
          {...register("specifications")}
        />
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Puede ingresar texto libre o JSON con especificaciones técnicas.
        </p>
      </div>

      {/* due_date */}
      <div className="space-y-1.5">
        <Label htmlFor="due_date">Fecha de entrega esperada</Label>
        <Input
          id="due_date"
          type="date"
          {...register("due_date")}
        />
      </div>

      {/* cost_cents */}
      <div className="space-y-1.5">
        <Label htmlFor="cost_cents">Costo (en centavos COP)</Label>
        <Input
          id="cost_cents"
          type="number"
          min={0}
          step={1}
          placeholder="Ej: 15000000 = $150.000 COP"
          {...register("cost_cents")}
          className={cn(errors.cost_cents && "border-red-500")}
        />
        {errors.cost_cents && (
          <p className="text-xs text-red-600">{errors.cost_cents.message}</p>
        )}
      </div>

      {/* notes */}
      <div className="space-y-1.5">
        <Label htmlFor="notes">Notas internas</Label>
        <Textarea
          id="notes"
          placeholder="Observaciones adicionales para el equipo..."
          rows={3}
          {...register("notes")}
        />
      </div>

      {/* Submit */}
      <div className="pt-2">
        <Button type="submit" disabled={isLoading} className="w-full sm:w-auto">
          {isLoading ? "Creando..." : "Crear orden"}
        </Button>
      </div>
    </form>
  );
}
