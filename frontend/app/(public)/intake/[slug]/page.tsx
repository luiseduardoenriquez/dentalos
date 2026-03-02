"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import axios from "axios";
import { getApiBaseUrl } from "@/lib/api-base-url";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { IntakeFormBuilder, type IntakeFieldValue } from "@/components/intake-form-builder";
import { CheckCircle2, ClipboardList, AlertTriangle, Loader2 } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface IntakeFieldDef {
  key: string;
  label: string;
  type: "text" | "email" | "phone" | "date" | "select" | "multiselect" | "checkbox" | "textarea";
  required: boolean;
  options?: string[];
  placeholder?: string;
}

interface IntakeFormConfig {
  template_id: string;
  clinic_name: string;
  form_name: string;
  description: string | null;
  fields: IntakeFieldDef[];
}

// ─── Public API (no auth) ─────────────────────────────────────────────────────

const publicClient = axios.create({
  baseURL: `${getApiBaseUrl()}/api/v1/public`,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PublicIntakePage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug ?? "";

  const { data: config, isLoading, isError } = useQuery({
    queryKey: ["public-intake", slug],
    queryFn: async () => {
      const { data } = await publicClient.get<IntakeFormConfig>(`/${slug}/intake/form`);
      return data;
    },
    retry: 1,
  });

  const { mutate: submitForm, isPending, isSuccess } = useMutation({
    mutationFn: async (payload: {
      patient_name: string;
      patient_email: string;
      patient_phone: string;
      responses: IntakeFieldValue[];
    }) => {
      await publicClient.post(`/${slug}/intake`, payload);
    },
  });

  const [patientName, setPatientName] = React.useState("");
  const [patientEmail, setPatientEmail] = React.useState("");
  const [patientPhone, setPatientPhone] = React.useState("");
  const [fieldValues, setFieldValues] = React.useState<IntakeFieldValue[]>([]);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    if (!patientName.trim() || !patientPhone.trim()) {
      setSubmitError("Nombre y teléfono son obligatorios.");
      return;
    }

    submitForm(
      {
        patient_name: patientName.trim(),
        patient_email: patientEmail.trim(),
        patient_phone: patientPhone.trim(),
        responses: fieldValues,
      },
      {
        onError: () =>
          setSubmitError("No se pudo enviar el formulario. Inténtalo de nuevo."),
      },
    );
  }

  // ─── Success screen ──────────────────────────────────────────────────────────

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center text-center py-12 gap-4">
            <div className="flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30">
              <CheckCircle2 className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                ¡Formulario enviado!
              </h2>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
                Hemos recibido tu información. La clínica se pondrá en contacto contigo
                próximamente.
              </p>
            </div>
            {config?.clinic_name && (
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {config.clinic_name}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  // ─── Error screen ────────────────────────────────────────────────────────────

  if (isError) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center text-center py-12 gap-4">
            <AlertTriangle className="h-10 w-10 text-orange-500" />
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                Formulario no disponible
              </h2>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
                No encontramos este formulario. Verifica el enlace o contacta a la clínica.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ─── Loading ─────────────────────────────────────────────────────────────────

  if (isLoading || !config) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg">
          <CardContent className="space-y-4 py-8">
            <Skeleton className="h-7 w-48 mx-auto" />
            <Skeleton className="h-4 w-64 mx-auto" />
            <div className="space-y-4 pt-4">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ─── Form ────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-start justify-center p-4 py-8">
      <Card className="w-full max-w-lg">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2 mb-1">
            <ClipboardList className="h-5 w-5 text-primary-600" />
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              {config.clinic_name}
            </span>
          </div>
          <CardTitle>{config.form_name}</CardTitle>
          {config.description && (
            <CardDescription>{config.description}</CardDescription>
          )}
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            {/* Basic identity fields — always shown */}
            <div className="space-y-4 pb-4 border-b border-[hsl(var(--border))]">
              <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                Datos de contacto
              </p>
              <div className="space-y-1">
                <Label htmlFor="patient-name">
                  Nombre completo{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="patient-name"
                  type="text"
                  autoComplete="name"
                  value={patientName}
                  onChange={(e) => setPatientName(e.target.value)}
                  placeholder="Ej: Ana María Gómez"
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="patient-phone">
                  Teléfono <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="patient-phone"
                  type="tel"
                  autoComplete="tel"
                  value={patientPhone}
                  onChange={(e) => setPatientPhone(e.target.value)}
                  placeholder="+573001234567"
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="patient-email">Correo electrónico</Label>
                <Input
                  id="patient-email"
                  type="email"
                  autoComplete="email"
                  value={patientEmail}
                  onChange={(e) => setPatientEmail(e.target.value)}
                  placeholder="correo@ejemplo.com (opcional)"
                />
              </div>
            </div>

            {/* Dynamic fields from template */}
            {config.fields.length > 0 && (
              <IntakeFormBuilder
                fields={config.fields}
                values={fieldValues}
                onChange={setFieldValues}
              />
            )}

            {/* Error message */}
            {submitError && (
              <p className="text-sm text-destructive">{submitError}</p>
            )}

            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Enviando...
                </>
              ) : (
                "Enviar formulario"
              )}
            </Button>

            <p className="text-xs text-center text-[hsl(var(--muted-foreground))]">
              Tu información es confidencial y solo será utilizada por la clínica.
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
