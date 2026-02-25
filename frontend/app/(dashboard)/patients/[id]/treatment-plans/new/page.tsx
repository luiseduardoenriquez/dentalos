"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ChevronRight,
  AlertCircle,
  Plus,
  Trash2,
  ClipboardList,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { usePatient } from "@/lib/hooks/use-patients";
import { useCreateTreatmentPlan } from "@/lib/hooks/use-treatment-plans";

// ─── Validation Schema ────────────────────────────────────────────────────────

const itemSchema = z.object({
  cups_code: z
    .string()
    .min(1, "Requerido")
    .regex(/^[0-9]{6}$/, "Código CUPS debe ser 6 dígitos"),
  cups_description: z.string().min(1, "Requerido").max(255),
  tooth_number: z
    .string()
    .optional()
    .transform((v) => (v ? parseInt(v, 10) : null))
    .refine((v) => v === null || (v >= 11 && v <= 88), {
      message: "Número de diente inválido (11–88)",
    }),
  estimated_cost_display: z
    .string()
    .min(1, "Requerido")
    .regex(/^[0-9]+$/, "Solo números")
    .transform((v) => parseInt(v, 10) * 100), // display in whole currency → store as cents
});

const formSchema = z
  .object({
    name: z.string().min(1, "Nombre requerido").max(150),
    description: z.string().max(500).optional(),
    auto_from_odontogram: z.boolean().default(false),
    items: z.array(itemSchema).optional(),
  })
  .superRefine((data, ctx) => {
    if (!data.auto_from_odontogram && (!data.items || data.items.length === 0)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "Agrega al menos un procedimiento o activa la generación automática desde el odontograma.",
        path: ["items"],
      });
    }
  });

type FormValues = z.infer<typeof formSchema>;

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function NewPlanSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-48" />
      </div>
      <Skeleton className="h-6 w-56" />
      <div className="space-y-4">
        <Skeleton className="h-10 w-full rounded-md" />
        <Skeleton className="h-20 w-full rounded-md" />
        <Skeleton className="h-10 w-64 rounded-md" />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewTreatmentPlanPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { mutate: createPlan, isPending } = useCreateTreatmentPlan(patientId);

  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      description: "",
      auto_from_odontogram: false,
      items: [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });

  const autoFromOdontogram = watch("auto_from_odontogram");

  function handleAddItem() {
    append({
      cups_code: "",
      cups_description: "",
      tooth_number: undefined,
      estimated_cost_display: "",
    } as unknown as FormValues["items"][0]);
  }

  function onSubmit(values: FormValues) {
    const payload = {
      name: values.name,
      description: values.description || null,
      auto_from_odontogram: values.auto_from_odontogram,
      items: values.auto_from_odontogram
        ? undefined
        : values.items?.map((item) => ({
            cups_code: item.cups_code,
            cups_description: item.cups_description,
            tooth_number: item.tooth_number ?? null,
            estimated_cost: item.estimated_cost_display, // already transformed to cents
          })),
    };

    createPlan(payload, {
      onSuccess: (plan) => {
        router.push(`/patients/${patientId}/treatment-plans/${plan.id}`);
      },
    });
  }

  if (isLoadingPatient) {
    return <NewPlanSkeleton />;
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
          href={`/patients/${patientId}/treatment-plans`}
          className="hover:text-foreground transition-colors"
        >
          Planes de tratamiento
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nuevo plan</span>
      </nav>

      {/* ─── Heading ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <ClipboardList className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">
          Nuevo plan de tratamiento
        </h1>
      </div>

      {/* ─── Form ────────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Información básica
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Name */}
            <div className="space-y-1.5">
              <label
                htmlFor="plan-name"
                className="text-sm font-medium text-foreground"
              >
                Nombre del plan{" "}
                <span className="text-destructive">*</span>
              </label>
              <Input
                id="plan-name"
                placeholder="Ej. Plan de rehabilitación oral"
                {...register("name")}
                disabled={isPending}
              />
              {errors.name && (
                <p className="text-xs text-destructive">{errors.name.message}</p>
              )}
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <label
                htmlFor="plan-description"
                className="text-sm font-medium text-foreground"
              >
                Descripción
              </label>
              <textarea
                id="plan-description"
                rows={3}
                placeholder="Observaciones generales del plan (opcional)"
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                {...register("description")}
                disabled={isPending}
              />
              {errors.description && (
                <p className="text-xs text-destructive">
                  {errors.description.message}
                </p>
              )}
            </div>

            {/* Auto-generate toggle */}
            <div className="flex items-start gap-3 rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--muted)/0.3)]">
              <Controller
                name="auto_from_odontogram"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="auto-from-odontogram"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    disabled={isPending}
                    className="mt-0.5"
                  />
                )}
              />
              <div>
                <label
                  htmlFor="auto-from-odontogram"
                  className="text-sm font-medium text-foreground cursor-pointer"
                >
                  Generar desde odontograma
                </label>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                  Importa automáticamente los procedimientos pendientes del
                  odontograma del paciente.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Manual items */}
        {!autoFromOdontogram && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">
                  Procedimientos
                </CardTitle>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddItem}
                  disabled={isPending}
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  Agregar
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {fields.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    No hay procedimientos. Agrega el primero.
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAddItem}
                    className="mt-3"
                    disabled={isPending}
                  >
                    <Plus className="mr-1.5 h-3.5 w-3.5" />
                    Agregar procedimiento
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[110px]">Código CUPS</TableHead>
                        <TableHead>Descripción</TableHead>
                        <TableHead className="w-[100px]">Diente</TableHead>
                        <TableHead className="w-[140px]">
                          Costo est. (COP)
                        </TableHead>
                        <TableHead className="w-[50px]" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {fields.map((field, index) => (
                        <TableRow key={field.id}>
                          <TableCell>
                            <Input
                              placeholder="809101"
                              className="h-8 text-sm font-mono"
                              {...register(`items.${index}.cups_code`)}
                              disabled={isPending}
                            />
                            {errors.items?.[index]?.cups_code && (
                              <p className="text-[10px] text-destructive mt-0.5">
                                {errors.items[index]?.cups_code?.message}
                              </p>
                            )}
                          </TableCell>
                          <TableCell>
                            <Input
                              placeholder="Descripción del procedimiento"
                              className="h-8 text-sm"
                              {...register(`items.${index}.cups_description`)}
                              disabled={isPending}
                            />
                            {errors.items?.[index]?.cups_description && (
                              <p className="text-[10px] text-destructive mt-0.5">
                                {errors.items[index]?.cups_description?.message}
                              </p>
                            )}
                          </TableCell>
                          <TableCell>
                            <Input
                              type="number"
                              placeholder="Ej. 11"
                              className="h-8 text-sm"
                              min={11}
                              max={88}
                              {...register(`items.${index}.tooth_number`)}
                              disabled={isPending}
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              type="number"
                              placeholder="150000"
                              className="h-8 text-sm tabular-nums"
                              min={0}
                              {...register(
                                `items.${index}.estimated_cost_display`,
                              )}
                              disabled={isPending}
                            />
                            {errors.items?.[index]?.estimated_cost_display && (
                              <p className="text-[10px] text-destructive mt-0.5">
                                {
                                  errors.items[index]?.estimated_cost_display
                                    ?.message
                                }
                              </p>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                              onClick={() => remove(index)}
                              disabled={isPending}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                              <span className="sr-only">Eliminar fila</span>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* Items-level error */}
              {errors.items && !Array.isArray(errors.items) && (
                <p className="text-xs text-destructive mt-2">
                  {(errors.items as { message?: string }).message}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Submit */}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              router.push(`/patients/${patientId}/treatment-plans`)
            }
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={isPending} className="min-w-[130px]">
            {isPending ? "Creando..." : "Crear plan"}
          </Button>
        </div>
      </form>
    </div>
  );
}
