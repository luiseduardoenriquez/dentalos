"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Separator } from "@/components/ui/separator";
import { useCreatePatient } from "@/lib/hooks/use-patients";
import {
  patientCreateSchema,
  type PatientCreateFormValues,
  DOCUMENT_TYPES,
  DOCUMENT_TYPE_LABELS,
  GENDERS,
  GENDER_LABELS,
  BLOOD_TYPES,
  REFERRAL_SOURCES,
  REFERRAL_SOURCE_LABELS,
} from "@/lib/validations/patient";

// ─── Form Field Error ─────────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-destructive-600 dark:text-destructive-400">{message}</p>;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewPatientPage() {
  const router = useRouter();
  const { mutate: createPatient, isPending } = useCreatePatient();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<PatientCreateFormValues>({
    resolver: zodResolver(patientCreateSchema),
    defaultValues: {
      document_type: "CC",
      allergies: [],
      chronic_conditions: [],
    },
  });

  // Comma-separated tags inputs (controlled as strings, transformed to arrays)
  const [allergiesInput, setAllergiesInput] = React.useState("");
  const [conditionsInput, setConditionsInput] = React.useState("");

  function onSubmit(values: PatientCreateFormValues) {
    // Parse comma-separated tag inputs
    const allergies = allergiesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const chronic_conditions = conditionsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = { ...values, allergies, chronic_conditions };

    createPatient(payload as Record<string, unknown>, {
      onSuccess: (patient) => {
        router.push(`/patients/${patient.id}`);
      },
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]" aria-label="Ruta de navegación">
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nuevo paciente</span>
      </nav>

      {/* ─── Page Title ──────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Nuevo paciente</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Completa la información para registrar al paciente.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        {/* ─── Section 1: Información personal ───────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Información personal</CardTitle>
            <CardDescription>Datos de identificación y datos personales del paciente.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Document Type */}
              <div className="space-y-1">
                <Label htmlFor="document_type">
                  Tipo de documento <span className="text-destructive-600">*</span>
                </Label>
                <Select
                  defaultValue="CC"
                  onValueChange={(val) =>
                    setValue("document_type", val as PatientCreateFormValues["document_type"], {
                      shouldValidate: true,
                    })
                  }
                >
                  <SelectTrigger id="document_type" aria-label="Tipo de documento">
                    <SelectValue placeholder="Selecciona tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {DOCUMENT_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {DOCUMENT_TYPE_LABELS[type]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.document_type?.message} />
              </div>

              {/* Document Number */}
              <div className="space-y-1">
                <Label htmlFor="document_number">
                  Número de documento <span className="text-destructive-600">*</span>
                </Label>
                <Input
                  id="document_number"
                  placeholder="Ej: 1234567890"
                  {...register("document_number")}
                  aria-invalid={!!errors.document_number}
                />
                <FieldError message={errors.document_number?.message} />
              </div>

              {/* First Name */}
              <div className="space-y-1">
                <Label htmlFor="first_name">
                  Nombres <span className="text-destructive-600">*</span>
                </Label>
                <Input
                  id="first_name"
                  placeholder="Ej: María José"
                  {...register("first_name")}
                  aria-invalid={!!errors.first_name}
                />
                <FieldError message={errors.first_name?.message} />
              </div>

              {/* Last Name */}
              <div className="space-y-1">
                <Label htmlFor="last_name">
                  Apellidos <span className="text-destructive-600">*</span>
                </Label>
                <Input
                  id="last_name"
                  placeholder="Ej: García López"
                  {...register("last_name")}
                  aria-invalid={!!errors.last_name}
                />
                <FieldError message={errors.last_name?.message} />
              </div>

              {/* Birthdate */}
              <div className="space-y-1">
                <Label htmlFor="birthdate">Fecha de nacimiento</Label>
                <Input
                  id="birthdate"
                  type="date"
                  {...register("birthdate")}
                  aria-invalid={!!errors.birthdate}
                />
                <FieldError message={errors.birthdate?.message} />
              </div>

              {/* Gender */}
              <div className="space-y-1">
                <Label htmlFor="gender">Género</Label>
                <Select
                  onValueChange={(val) =>
                    setValue("gender", val as PatientCreateFormValues["gender"], {
                      shouldValidate: true,
                    })
                  }
                >
                  <SelectTrigger id="gender" aria-label="Género">
                    <SelectValue placeholder="Selecciona género" />
                  </SelectTrigger>
                  <SelectContent>
                    {GENDERS.map((g) => (
                      <SelectItem key={g} value={g}>
                        {GENDER_LABELS[g]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.gender?.message} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ─── Section 2: Contacto ─────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contacto</CardTitle>
            <CardDescription>Teléfonos, correo y dirección del paciente.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="phone">Teléfono principal</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="+573001234567"
                  {...register("phone")}
                  aria-invalid={!!errors.phone}
                />
                <FieldError message={errors.phone?.message} />
              </div>

              <div className="space-y-1">
                <Label htmlFor="phone_secondary">Teléfono secundario</Label>
                <Input
                  id="phone_secondary"
                  type="tel"
                  placeholder="+573001234567"
                  {...register("phone_secondary")}
                  aria-invalid={!!errors.phone_secondary}
                />
                <FieldError message={errors.phone_secondary?.message} />
              </div>

              <div className="space-y-1 sm:col-span-2">
                <Label htmlFor="email">Correo electrónico</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="paciente@ejemplo.com"
                  {...register("email")}
                  aria-invalid={!!errors.email}
                />
                <FieldError message={errors.email?.message} />
              </div>

              <div className="space-y-1 sm:col-span-2">
                <Label htmlFor="address">Dirección</Label>
                <Input
                  id="address"
                  placeholder="Ej: Calle 123 # 45-67, Apto 201"
                  {...register("address")}
                  aria-invalid={!!errors.address}
                />
                <FieldError message={errors.address?.message} />
              </div>

              <div className="space-y-1">
                <Label htmlFor="city">Ciudad</Label>
                <Input
                  id="city"
                  placeholder="Ej: Bogotá"
                  {...register("city")}
                  aria-invalid={!!errors.city}
                />
                <FieldError message={errors.city?.message} />
              </div>

              <div className="space-y-1">
                <Label htmlFor="state_province">Departamento</Label>
                <Input
                  id="state_province"
                  placeholder="Ej: Cundinamarca"
                  {...register("state_province")}
                  aria-invalid={!!errors.state_province}
                />
                <FieldError message={errors.state_province?.message} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ─── Section 3: Contacto de emergencia ──────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contacto de emergencia</CardTitle>
            <CardDescription>Persona a contactar en caso de emergencia.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="emergency_contact_name">Nombre del contacto</Label>
                <Input
                  id="emergency_contact_name"
                  placeholder="Ej: Carlos García"
                  {...register("emergency_contact_name")}
                  aria-invalid={!!errors.emergency_contact_name}
                />
                <FieldError message={errors.emergency_contact_name?.message} />
              </div>

              <div className="space-y-1">
                <Label htmlFor="emergency_contact_phone">Teléfono del contacto</Label>
                <Input
                  id="emergency_contact_phone"
                  type="tel"
                  placeholder="+573001234567"
                  {...register("emergency_contact_phone")}
                  aria-invalid={!!errors.emergency_contact_phone}
                />
                <FieldError message={errors.emergency_contact_phone?.message} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ─── Section 4: Información médica ──────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Información médica</CardTitle>
            <CardDescription>
              Datos de aseguradora, antecedentes y cómo llegó el paciente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="insurance_provider">Aseguradora / EPS</Label>
                <Input
                  id="insurance_provider"
                  placeholder="Ej: Sura, Compensar, Sanitas"
                  {...register("insurance_provider")}
                  aria-invalid={!!errors.insurance_provider}
                />
                <FieldError message={errors.insurance_provider?.message} />
              </div>

              <div className="space-y-1">
                <Label htmlFor="insurance_policy_number">Número de póliza / carné</Label>
                <Input
                  id="insurance_policy_number"
                  placeholder="Ej: 0012345678"
                  {...register("insurance_policy_number")}
                  aria-invalid={!!errors.insurance_policy_number}
                />
                <FieldError message={errors.insurance_policy_number?.message} />
              </div>

              <div className="space-y-1">
                <Label htmlFor="blood_type">Tipo de sangre</Label>
                <Select
                  onValueChange={(val) =>
                    setValue("blood_type", val as PatientCreateFormValues["blood_type"], {
                      shouldValidate: true,
                    })
                  }
                >
                  <SelectTrigger id="blood_type" aria-label="Tipo de sangre">
                    <SelectValue placeholder="Selecciona tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {BLOOD_TYPES.map((bt) => (
                      <SelectItem key={bt} value={bt}>
                        {bt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.blood_type?.message} />
              </div>

              <div className="space-y-1">
                <Label htmlFor="referral_source">¿Cómo nos conoció?</Label>
                <Select
                  onValueChange={(val) =>
                    setValue("referral_source", val as PatientCreateFormValues["referral_source"], {
                      shouldValidate: true,
                    })
                  }
                >
                  <SelectTrigger id="referral_source" aria-label="Fuente de referido">
                    <SelectValue placeholder="Selecciona fuente" />
                  </SelectTrigger>
                  <SelectContent>
                    {REFERRAL_SOURCES.map((src) => (
                      <SelectItem key={src} value={src}>
                        {REFERRAL_SOURCE_LABELS[src]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.referral_source?.message} />
              </div>
            </div>

            <Separator />

            {/* Allergies */}
            <div className="space-y-1">
              <Label htmlFor="allergies">Alergias</Label>
              <Input
                id="allergies"
                placeholder="Ej: Penicilina, látex, ibuprofeno (separadas por coma)"
                value={allergiesInput}
                onChange={(e) => setAllergiesInput(e.target.value)}
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Ingresa las alergias separadas por coma.
              </p>
            </div>

            {/* Chronic Conditions */}
            <div className="space-y-1">
              <Label htmlFor="chronic_conditions">Enfermedades crónicas</Label>
              <Input
                id="chronic_conditions"
                placeholder="Ej: Diabetes, hipertensión (separadas por coma)"
                value={conditionsInput}
                onChange={(e) => setConditionsInput(e.target.value)}
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Ingresa las condiciones separadas por coma.
              </p>
            </div>

            {/* Notes */}
            <div className="space-y-1">
              <Label htmlFor="notes">Notas adicionales</Label>
              <textarea
                id="notes"
                rows={3}
                placeholder="Observaciones generales sobre el paciente..."
                {...register("notes")}
                className="flex w-full rounded-md border border-[hsl(var(--input))] bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-600 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                aria-invalid={!!errors.notes}
              />
              <FieldError message={errors.notes?.message} />
            </div>
          </CardContent>
        </Card>

        {/* ─── Action Buttons ──────────────────────────────────────────────── */}
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" asChild>
            <Link href="/patients">Cancelar</Link>
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? "Guardando..." : "Guardar paciente"}
          </Button>
        </div>
      </form>
    </div>
  );
}
