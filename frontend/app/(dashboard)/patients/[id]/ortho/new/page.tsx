"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ChevronRight,
  AlertCircle,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { usePatient } from "@/lib/hooks/use-patients";
import { useCreateOrthoCase } from "@/lib/hooks/use-ortho";
import {
  APPLIANCE_TYPES,
  ANGLE_CLASSES,
  APPLIANCE_TYPE_LABELS,
  ANGLE_CLASS_LABELS,
} from "@/lib/validations/ortho";

// ─── Form Schema ──────────────────────────────────────────────────────────────
//
// Money fields are collected as whole-COP display strings and transformed to
// integer cents on submit, matching the backend's convention of storing all
// money as integer cents.

const formSchema = z.object({
  appliance_type: z.enum(APPLIANCE_TYPES, {
    errorMap: () => ({ message: "Selecciona un tipo de aparato" }),
  }),

  angle_class: z
    .enum(ANGLE_CLASSES, {
      errorMap: () => ({ message: "Clase de Angle inválida" }),
    })
    .optional()
    .nullable(),

  malocclusion_type: z
    .string()
    .max(200, "No puede exceder 200 caracteres")
    .optional(),

  estimated_duration_months: z
    .string()
    .optional()
    .transform((v) => (v && v.trim() !== "" ? parseInt(v, 10) : null))
    .refine((v) => v === null || (Number.isInteger(v) && v >= 1 && v <= 120), {
      message: "La duración debe ser entre 1 y 120 meses",
    }),

  // Display as whole COP; transform to cents on submit
  total_cost_estimated_display: z
    .string()
    .optional()
    .transform((v) =>
      v && v.trim() !== "" ? parseInt(v.trim(), 10) * 100 : undefined,
    )
    .refine((v) => v === undefined || (Number.isInteger(v) && v >= 0), {
      message: "El costo estimado debe ser un número entero positivo",
    }),

  initial_payment_display: z
    .string()
    .optional()
    .transform((v) =>
      v && v.trim() !== "" ? parseInt(v.trim(), 10) * 100 : undefined,
    )
    .refine((v) => v === undefined || (Number.isInteger(v) && v >= 0), {
      message: "El pago inicial debe ser un número entero positivo",
    }),

  monthly_payment_display: z
    .string()
    .optional()
    .transform((v) =>
      v && v.trim() !== "" ? parseInt(v.trim(), 10) * 100 : undefined,
    )
    .refine((v) => v === undefined || (Number.isInteger(v) && v >= 0), {
      message: "El pago mensual debe ser un número entero positivo",
    }),

  notes: z
    .string()
    .max(2000, "Las notas no pueden exceder 2000 caracteres")
    .optional(),
});

type FormValues = z.input<typeof formSchema>;
type FormOutput = z.output<typeof formSchema>;

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function NewOrthoCaseSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      <Skeleton className="h-6 w-56" />
      <div className="space-y-4">
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewOrthoCasePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { mutate: createCase, isPending } = useCreateOrthoCase(patientId);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      appliance_type: undefined,
      angle_class: null,
      malocclusion_type: "",
      estimated_duration_months: "",
      total_cost_estimated_display: "",
      initial_payment_display: "",
      monthly_payment_display: "",
      notes: "",
    },
  });

  function onSubmit(values: FormValues) {
    // Cast to output type — Zod transforms have already run
    const out = values as unknown as FormOutput;

    createCase(
      {
        appliance_type: out.appliance_type,
        angle_class: out.angle_class ?? null,
        malocclusion_type: out.malocclusion_type?.trim() || null,
        estimated_duration_months: out.estimated_duration_months ?? null,
        total_cost_estimated: out.total_cost_estimated_display,
        initial_payment: out.initial_payment_display,
        monthly_payment: out.monthly_payment_display,
        notes: out.notes?.trim() || null,
      },
      {
        onSuccess: (created) => {
          router.push(`/patients/${patientId}/ortho/${created.id}`);
        },
      },
    );
  }

  if (isLoadingPatient) {
    return <NewOrthoCaseSkeleton />;
  }

  if (!patient) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Paciente no encontrado"
        description="El paciente que buscas no existe o no tienes permiso para verlo."
        action={{ label: "Volver a pacientes", href: "/patients" }}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}`}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {patient.full_name}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}/ortho`}
          className="hover:text-foreground transition-colors"
        >
          Ortodoncia
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nuevo caso</span>
      </nav>

      {/* ─── Heading ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Wrench className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">
          Nuevo caso de ortodoncia
        </h1>
      </div>

      {/* ─── Form ────────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

        {/* ─── Card: Información del caso ─────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Información del caso
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">

            {/* Appliance type */}
            <div className="space-y-1.5">
              <label
                htmlFor="appliance-type"
                className="text-sm font-medium text-foreground"
              >
                Tipo de aparatología{" "}
                <span className="text-destructive">*</span>
              </label>
              <Controller
                name="appliance_type"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value ?? ""}
                    onValueChange={field.onChange}
                    disabled={isPending}
                  >
                    <SelectTrigger id="appliance-type">
                      <SelectValue placeholder="Selecciona un tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      {APPLIANCE_TYPES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {APPLIANCE_TYPE_LABELS[type]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.appliance_type && (
                <p className="text-xs text-destructive">
                  {errors.appliance_type.message}
                </p>
              )}
            </div>

            {/* Angle class */}
            <div className="space-y-1.5">
              <label
                htmlFor="angle-class"
                className="text-sm font-medium text-foreground"
              >
                Clase de Angle
              </label>
              <Controller
                name="angle_class"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value ?? ""}
                    onValueChange={(val) =>
                      field.onChange(val === "" ? null : val)
                    }
                    disabled={isPending}
                  >
                    <SelectTrigger id="angle-class">
                      <SelectValue placeholder="Selecciona una clase (opcional)" />
                    </SelectTrigger>
                    <SelectContent>
                      {ANGLE_CLASSES.map((cls) => (
                        <SelectItem key={cls} value={cls}>
                          {ANGLE_CLASS_LABELS[cls]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.angle_class && (
                <p className="text-xs text-destructive">
                  {errors.angle_class.message}
                </p>
              )}
            </div>

            {/* Malocclusion type */}
            <div className="space-y-1.5">
              <label
                htmlFor="malocclusion-type"
                className="text-sm font-medium text-foreground"
              >
                Tipo de maloclusión
              </label>
              <Input
                id="malocclusion-type"
                placeholder="Ej. Apiñamiento severo superior (opcional)"
                {...register("malocclusion_type")}
                disabled={isPending}
              />
              {errors.malocclusion_type && (
                <p className="text-xs text-destructive">
                  {errors.malocclusion_type.message}
                </p>
              )}
            </div>

            {/* Estimated duration */}
            <div className="space-y-1.5">
              <label
                htmlFor="estimated-duration"
                className="text-sm font-medium text-foreground"
              >
                Duración estimada (meses)
              </label>
              <Input
                id="estimated-duration"
                type="number"
                placeholder="Ej. 24"
                min={1}
                max={120}
                {...register("estimated_duration_months")}
                disabled={isPending}
              />
              {errors.estimated_duration_months && (
                <p className="text-xs text-destructive">
                  {errors.estimated_duration_months.message}
                </p>
              )}
            </div>

          </CardContent>
        </Card>

        {/* ─── Card: Financiero ────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">Financiero</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">

            {/* Total cost estimated */}
            <div className="space-y-1.5">
              <label
                htmlFor="total-cost"
                className="text-sm font-medium text-foreground"
              >
                Costo estimado total (COP)
              </label>
              <Input
                id="total-cost"
                type="number"
                placeholder="Ej. 3500000"
                min={0}
                className="tabular-nums"
                {...register("total_cost_estimated_display")}
                disabled={isPending}
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Ingresa el valor en pesos colombianos enteros. Se almacena en centavos.
              </p>
              {errors.total_cost_estimated_display && (
                <p className="text-xs text-destructive">
                  {errors.total_cost_estimated_display.message}
                </p>
              )}
            </div>

            {/* Initial payment */}
            <div className="space-y-1.5">
              <label
                htmlFor="initial-payment"
                className="text-sm font-medium text-foreground"
              >
                Pago inicial (COP)
              </label>
              <Input
                id="initial-payment"
                type="number"
                placeholder="Ej. 500000"
                min={0}
                className="tabular-nums"
                {...register("initial_payment_display")}
                disabled={isPending}
              />
              {errors.initial_payment_display && (
                <p className="text-xs text-destructive">
                  {errors.initial_payment_display.message}
                </p>
              )}
            </div>

            {/* Monthly payment */}
            <div className="space-y-1.5">
              <label
                htmlFor="monthly-payment"
                className="text-sm font-medium text-foreground"
              >
                Pago mensual (COP)
              </label>
              <Input
                id="monthly-payment"
                type="number"
                placeholder="Ej. 150000"
                min={0}
                className="tabular-nums"
                {...register("monthly_payment_display")}
                disabled={isPending}
              />
              {errors.monthly_payment_display && (
                <p className="text-xs text-destructive">
                  {errors.monthly_payment_display.message}
                </p>
              )}
            </div>

          </CardContent>
        </Card>

        {/* ─── Card: Notas ─────────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">Notas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              <label
                htmlFor="notes"
                className="text-sm font-medium text-foreground"
              >
                Observaciones generales
              </label>
              <textarea
                id="notes"
                rows={4}
                placeholder="Observaciones iniciales del caso (opcional)"
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                {...register("notes")}
                disabled={isPending}
              />
              {errors.notes && (
                <p className="text-xs text-destructive">
                  {errors.notes.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* ─── Submit ──────────────────────────────────────────────────── */}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push(`/patients/${patientId}/ortho`)}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={isPending} className="min-w-[130px]">
            {isPending ? "Creando..." : "Crear caso"}
          </Button>
        </div>

      </form>
    </div>
  );
}
