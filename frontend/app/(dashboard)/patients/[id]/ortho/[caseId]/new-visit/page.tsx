"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronRight, AlertCircle, CalendarDays } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { usePatient } from "@/lib/hooks/use-patients";
import { useOrthoCase, useCreateOrthoVisit } from "@/lib/hooks/use-ortho";
import {
  orthoVisitCreateSchema,
  type OrthoVisitCreateForm,
} from "@/lib/validations/ortho";

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function NewVisitSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        {[16, 4, 28, 4, 24, 4, 24, 4, 28].map((w, i) => (
          <Skeleton key={i} className={`h-4 w-${w}`} />
        ))}
      </div>
      <Skeleton className="h-6 w-48" />
      <div className="space-y-4">
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewOrthoVisitPage() {
  const params = useParams<{ id: string; caseId: string }>();
  const router = useRouter();
  const { id: patientId, caseId } = params;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: orthoCase, isLoading: isLoadingCase } = useOrthoCase(
    patientId,
    caseId,
  );
  const { mutate: createVisit, isPending } = useCreateOrthoVisit(
    patientId,
    caseId,
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<OrthoVisitCreateForm>({
    resolver: zodResolver(orthoVisitCreateSchema),
    defaultValues: {
      visit_date: new Date().toISOString().split("T")[0],
      wire_upper: "",
      wire_lower: "",
      elastics: "",
      adjustments: "",
      next_visit_date: "",
      payment_amount: undefined,
      notes: "",
    },
  });

  function onSubmit(values: OrthoVisitCreateForm) {
    // payment_amount comes from the form as whole COP; convert to cents
    const payload = {
      ...values,
      payment_amount:
        values.payment_amount != null && values.payment_amount > 0
          ? Math.round(values.payment_amount * 100)
          : undefined,
      // Normalize empty strings to null for optional fields
      wire_upper: values.wire_upper?.trim() || null,
      wire_lower: values.wire_lower?.trim() || null,
      elastics: values.elastics?.trim() || null,
      adjustments: values.adjustments?.trim() || null,
      next_visit_date: values.next_visit_date?.trim() || null,
      notes: values.notes?.trim() || null,
    };

    createVisit(payload, {
      onSuccess: () => {
        router.push(`/patients/${patientId}/ortho/${caseId}`);
      },
    });
  }

  const isLoading = isLoadingPatient || isLoadingCase;

  if (isLoading) {
    return <NewVisitSkeleton />;
  }

  if (!patient || !orthoCase) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Caso no encontrado"
        description="El caso de ortodoncia que buscas no existe o no tienes permiso para verlo."
        action={{
          label: "Volver",
          href: `/patients/${patientId}/ortho`,
        }}
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
        <Link
          href="/patients"
          className="hover:text-foreground transition-colors"
        >
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}`}
          className="hover:text-foreground transition-colors truncate max-w-[130px]"
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
        <Link
          href={`/patients/${patientId}/ortho/${caseId}`}
          className="hover:text-foreground transition-colors"
        >
          {orthoCase.case_number}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nueva visita</span>
      </nav>

      {/* ─── Heading ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <CalendarDays className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">
          Registrar visita de control
        </h1>
      </div>

      {/* ─── Form ────────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        {/* Fechas y arcos */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Datos de la visita
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Fecha de visita */}
            <div className="space-y-1.5">
              <Label htmlFor="visit_date" required>
                Fecha de visita
              </Label>
              <Input
                id="visit_date"
                type="date"
                {...register("visit_date")}
                disabled={isPending}
              />
              {errors.visit_date && (
                <p className="text-xs text-destructive">
                  {errors.visit_date.message}
                </p>
              )}
            </div>

            {/* Próxima visita */}
            <div className="space-y-1.5">
              <Label htmlFor="next_visit_date">Próxima visita</Label>
              <Input
                id="next_visit_date"
                type="date"
                {...register("next_visit_date")}
                disabled={isPending}
              />
              {errors.next_visit_date && (
                <p className="text-xs text-destructive">
                  {errors.next_visit_date.message}
                </p>
              )}
            </div>

            {/* Arco superior */}
            <div className="space-y-1.5">
              <Label htmlFor="wire_upper">Arco superior</Label>
              <Input
                id="wire_upper"
                type="text"
                placeholder="Ej. 0.014 NiTi"
                {...register("wire_upper")}
                disabled={isPending}
              />
              {errors.wire_upper && (
                <p className="text-xs text-destructive">
                  {errors.wire_upper.message}
                </p>
              )}
            </div>

            {/* Arco inferior */}
            <div className="space-y-1.5">
              <Label htmlFor="wire_lower">Arco inferior</Label>
              <Input
                id="wire_lower"
                type="text"
                placeholder="Ej. 0.014 NiTi"
                {...register("wire_lower")}
                disabled={isPending}
              />
              {errors.wire_lower && (
                <p className="text-xs text-destructive">
                  {errors.wire_lower.message}
                </p>
              )}
            </div>

            {/* Elásticos */}
            <div className="space-y-1.5">
              <Label htmlFor="elastics">Elásticos</Label>
              <Input
                id="elastics"
                type="text"
                placeholder="Ej. Clase II bilateral 3/16&quot;"
                {...register("elastics")}
                disabled={isPending}
              />
              {errors.elastics && (
                <p className="text-xs text-destructive">
                  {errors.elastics.message}
                </p>
              )}
            </div>

            {/* Monto de pago */}
            <div className="space-y-1.5">
              <Label htmlFor="payment_amount">Monto (COP)</Label>
              <Input
                id="payment_amount"
                type="number"
                min={0}
                placeholder="Ej. 150000"
                className="tabular-nums"
                {...register("payment_amount", {
                  setValueAs: (v) =>
                    v === "" || v === undefined ? undefined : Number(v),
                })}
                disabled={isPending}
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Ingresa el valor en pesos colombianos (sin centavos)
              </p>
              {errors.payment_amount && (
                <p className="text-xs text-destructive">
                  {errors.payment_amount.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Ajustes y notas */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Observaciones clínicas
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Ajustes realizados */}
            <div className="space-y-1.5">
              <Label htmlFor="adjustments">Ajustes realizados</Label>
              <textarea
                id="adjustments"
                rows={3}
                placeholder="Describe los ajustes realizados durante esta visita..."
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                {...register("adjustments")}
                disabled={isPending}
              />
              {errors.adjustments && (
                <p className="text-xs text-destructive">
                  {errors.adjustments.message}
                </p>
              )}
            </div>

            {/* Notas adicionales */}
            <div className="space-y-1.5">
              <Label htmlFor="notes">Notas adicionales</Label>
              <textarea
                id="notes"
                rows={2}
                placeholder="Observaciones adicionales (opcional)"
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

        {/* Submit */}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              router.push(`/patients/${patientId}/ortho/${caseId}`)
            }
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" disabled={isPending} className="min-w-[140px]">
            {isPending ? "Registrando..." : "Registrar visita"}
          </Button>
        </div>
      </form>
    </div>
  );
}
