"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChevronRight, PlusCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MedicationFormCard } from "@/components/medication-form-card";
import { useCreatePrescription } from "@/lib/hooks/use-prescriptions";
import { useDiagnoses } from "@/lib/hooks/use-diagnoses";
import {
  prescriptionCreateSchema,
  type PrescriptionCreate,
  type MedicationItemFormValues,
} from "@/lib/validations/prescription";
import { toast } from "sonner";

// ─── Default medication blank item ───────────────────────────────────────────

function blankMedication(): MedicationItemFormValues {
  return {
    name: "",
    dosis: "",
    frecuencia: "",
    duracion_dias: 1,
    via: "oral",
    instrucciones: null,
  };
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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewPrescriptionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  // ─── Local State ──────────────────────────────────────────────────────────
  const [medications, setMedications] = React.useState<MedicationItemFormValues[]>([
    blankMedication(),
  ]);
  const [diagnosis_id, setDiagnosisId] = React.useState<string>("");
  const [notes, setNotes] = React.useState<string>("");
  const [formErrors, setFormErrors] = React.useState<Record<string, string>>({});
  const [medicationErrors, setMedicationErrors] = React.useState<
    Record<number, Record<string, string>>
  >({});

  // ─── Queries & Mutations ──────────────────────────────────────────────────
  const { data: diagnosesData } = useDiagnoses(params.id, "active");
  const activeDiagnoses = diagnosesData?.items ?? [];

  const { mutate: createPrescription, isPending } = useCreatePrescription(params.id);

  // ─── Medication Handlers ──────────────────────────────────────────────────

  function handleMedicationChange(index: number, field: string, value: string | number) {
    setMedications((prev) =>
      prev.map((med, i) => (i === index ? { ...med, [field]: value } : med)),
    );
    // Clear field-level error on change
    setMedicationErrors((prev) => {
      const updated = { ...prev };
      if (updated[index]) {
        const { [field]: _removed, ...rest } = updated[index];
        updated[index] = rest;
      }
      return updated;
    });
  }

  function handleAddMedication() {
    if (medications.length >= 20) {
      toast.error("Se permiten máximo 20 medicamentos por prescripción.");
      return;
    }
    setMedications((prev) => [...prev, blankMedication()]);
  }

  function handleRemoveMedication(index: number) {
    if (medications.length <= 1) {
      toast.error("La prescripción debe tener al menos un medicamento.");
      return;
    }
    setMedications((prev) => prev.filter((_, i) => i !== index));
    setMedicationErrors((prev) => {
      const updated: Record<number, Record<string, string>> = {};
      Object.entries(prev).forEach(([k, v]) => {
        const num = Number(k);
        if (num < index) updated[num] = v;
        else if (num > index) updated[num - 1] = v;
      });
      return updated;
    });
  }

  // ─── Submit ───────────────────────────────────────────────────────────────

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const payload: PrescriptionCreate = {
      medications,
      diagnosis_id: diagnosis_id || null,
      notes: notes.trim() || null,
    };

    const result = prescriptionCreateSchema.safeParse(payload);

    if (!result.success) {
      const topErrors: Record<string, string> = {};
      const medErrs: Record<number, Record<string, string>> = {};

      result.error.errors.forEach((err) => {
        const path = err.path;
        // Medication item field: path = ["medications", 0, "name"]
        if (path[0] === "medications" && typeof path[1] === "number" && path[2]) {
          const idx = path[1];
          const field = String(path[2]);
          if (!medErrs[idx]) medErrs[idx] = {};
          medErrs[idx][field] = err.message;
        } else if (path[0] === "medications" && path.length === 1) {
          topErrors.medications = err.message;
        } else {
          topErrors[String(path[0])] = err.message;
        }
      });

      setFormErrors(topErrors);
      setMedicationErrors(medErrs);
      return;
    }

    setFormErrors({});
    setMedicationErrors({});

    createPrescription(result.data, {
      onSuccess: () => {
        router.push(`/patients/${params.id}/prescriptions`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
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
          href={`/patients/${params.id}`}
          className="hover:text-foreground transition-colors"
        >
          Detalle del paciente
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${params.id}/prescriptions`}
          className="hover:text-foreground transition-colors"
        >
          Prescripciones
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nueva prescripción</span>
      </nav>

      {/* ─── Page Title ──────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Nueva prescripción</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Agrega los medicamentos y completa los datos de la prescripción.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* ─── Section: Medicamentos ───────────────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground">Medicamentos</h2>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
                Agrega uno o más medicamentos a la prescripción.
              </p>
            </div>
          </div>

          {/* Medication cards list */}
          <div className="space-y-3">
            {medications.map((med, idx) => (
              <MedicationFormCard
                key={idx}
                index={idx}
                medication={med}
                onChange={handleMedicationChange}
                onRemove={handleRemoveMedication}
                errors={medicationErrors[idx] ?? {}}
              />
            ))}
          </div>

          {/* Top-level medications error */}
          {formErrors.medications && (
            <div className="flex items-center gap-2 text-destructive-600 text-sm">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{formErrors.medications}</span>
            </div>
          )}

          {/* Add medication button */}
          {medications.length < 20 && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddMedication}
              className="w-full border-dashed"
            >
              <PlusCircle className="mr-2 h-4 w-4" />
              Agregar medicamento
            </Button>
          )}
        </div>

        {/* ─── Section: Detalles adicionales ──────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Detalles adicionales</CardTitle>
            <CardDescription>Información complementaria de la prescripción.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Diagnosis link */}
            <div className="space-y-1">
              <Label htmlFor="diagnosis_id">
                Diagnóstico relacionado{" "}
                <span className="text-xs text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </Label>
              <Select
                value={diagnosis_id}
                onValueChange={(val) => {
                  setDiagnosisId(val === "__none__" ? "" : val);
                }}
              >
                <SelectTrigger id="diagnosis_id" aria-label="Diagnóstico relacionado">
                  <SelectValue placeholder="Selecciona un diagnóstico" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Sin diagnóstico asociado</SelectItem>
                  {activeDiagnoses.map((dx) => (
                    <SelectItem key={dx.id} value={dx.id}>
                      <span className="font-mono text-xs mr-2">{dx.cie10_code}</span>
                      {dx.cie10_description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FieldError message={formErrors.diagnosis_id} />
            </div>

            {/* Notes */}
            <div className="space-y-1">
              <Label htmlFor="notes">
                Notas{" "}
                <span className="text-xs text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </Label>
              <textarea
                id="notes"
                rows={3}
                placeholder="Instrucciones generales, contraindicaciones, observaciones..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="flex w-full rounded-md border border-[hsl(var(--input))] bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-600 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                aria-invalid={Boolean(formErrors.notes)}
              />
              <FieldError message={formErrors.notes} />
            </div>
          </CardContent>
        </Card>

        {/* ─── Action Buttons ──────────────────────────────────────────────── */}
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" asChild>
            <Link href={`/patients/${params.id}/prescriptions`}>Cancelar</Link>
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? "Guardando..." : "Crear prescripción"}
          </Button>
        </div>
      </form>
    </div>
  );
}
