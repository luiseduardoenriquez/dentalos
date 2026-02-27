"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChevronRight, ChevronLeft, Eye, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ConsentPreview } from "@/components/consent-preview";
import { useConsentTemplates, useConsentTemplate } from "@/lib/hooks/use-consent-templates";
import { useCreateConsent } from "@/lib/hooks/use-consents";
import { usePatient } from "@/lib/hooks/use-patients";

// ─── Category Labels ──────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  general: "General",
  surgery: "Cirugía",
  sedation: "Sedación",
  orthodontics: "Ortodoncia",
  implants: "Implantes",
  endodontics: "Endodoncia",
  pediatric: "Pediátrico",
};

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function NewConsentSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full rounded-md" />
          <Skeleton className="h-4 w-64" />
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Step Indicator ───────────────────────────────────────────────────────────

function StepIndicator({ current_step }: { current_step: 1 | 2 }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <div
        className={
          current_step === 1
            ? "flex h-6 w-6 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white"
            : "flex h-6 w-6 items-center justify-center rounded-full bg-success-50 border border-success-500/30 text-xs font-bold text-success-700"
        }
      >
        1
      </div>
      <span
        className={
          current_step === 1 ? "font-semibold text-foreground" : "text-[hsl(var(--muted-foreground))]"
        }
      >
        Seleccionar plantilla
      </span>

      <ChevronRight className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />

      <div
        className={
          current_step === 2
            ? "flex h-6 w-6 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white"
            : "flex h-6 w-6 items-center justify-center rounded-full bg-[hsl(var(--muted))] text-xs font-bold text-[hsl(var(--muted-foreground))]"
        }
      >
        2
      </div>
      <span
        className={
          current_step === 2 ? "font-semibold text-foreground" : "text-[hsl(var(--muted-foreground))]"
        }
      >
        Vista previa
      </span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewConsentPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patient_id = params.id;

  const [step, set_step] = React.useState<1 | 2>(1);
  const [selected_template_id, set_selected_template_id] = React.useState<string>("");

  const { data: patient, isLoading: is_loading_patient } = usePatient(patient_id);
  const { data: templates, isLoading: is_loading_templates } = useConsentTemplates();
  const { data: selected_template, isLoading: is_loading_template_detail } =
    useConsentTemplate(selected_template_id || null);
  const { mutate: create_consent, isPending: is_creating } = useCreateConsent(patient_id);

  const is_loading = is_loading_patient || is_loading_templates;

  // Group active templates by category
  const templates_by_category = React.useMemo(() => {
    if (!templates) return {} as Record<string, typeof templates>;
    const active = templates.filter((t) => t.is_active);
    return active.reduce(
      (acc, template) => {
        const cat = template.category;
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(template);
        return acc;
      },
      {} as Record<string, typeof active>,
    );
  }, [templates]);

  const category_keys = Object.keys(templates_by_category);

  function handle_next() {
    if (!selected_template_id) return;
    set_step(2);
  }

  function handle_back() {
    set_step(1);
  }

  function handle_create() {
    create_consent(
      { template_id: selected_template_id },
      {
        onSuccess: (consent) => {
          router.push(`/patients/${patient_id}/consents/${consent.id}`);
        },
      },
    );
  }

  if (is_loading) {
    return <NewConsentSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* ─── Breadcrumb ────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patient_id}`}
          className="hover:text-foreground transition-colors truncate max-w-[120px]"
        >
          {patient?.full_name ?? "Paciente"}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patient_id}/consents`}
          className="hover:text-foreground transition-colors"
        >
          Consentimientos
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nuevo</span>
      </nav>

      {/* ─── Header ────────────────────────────────────────────────── */}
      <div className="space-y-1">
        <h1 className="text-xl font-bold text-foreground">Nuevo consentimiento informado</h1>
        <StepIndicator current_step={step} />
      </div>

      {/* ─── Step 1: Template Selection ────────────────────────────── */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Seleccionar plantilla</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {category_keys.length === 0 ? (
              <div className="flex items-center gap-2 rounded-md border border-warning-300 bg-warning-50 px-4 py-3 text-sm text-warning-700 dark:border-warning-700 dark:bg-warning-900/20 dark:text-warning-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>
                  No hay plantillas de consentimiento disponibles. Contacta al administrador.
                </span>
              </div>
            ) : (
              <div className="space-y-2">
                <label
                  htmlFor="template-select"
                  className="text-sm font-medium text-foreground"
                >
                  Plantilla de consentimiento{" "}
                  <span className="text-destructive-600">*</span>
                </label>
                <Select
                  value={selected_template_id}
                  onValueChange={set_selected_template_id}
                >
                  <SelectTrigger id="template-select" className="w-full">
                    <SelectValue placeholder="Selecciona una plantilla..." />
                  </SelectTrigger>
                  <SelectContent>
                    {category_keys.map((category) => (
                      <SelectGroup key={category}>
                        <SelectLabel>
                          {CATEGORY_LABELS[category] ?? category}
                        </SelectLabel>
                        {templates_by_category[category]?.map((template) => (
                          <SelectItem key={template.id} value={template.id}>
                            {template.name}
                            {template.is_builtin && (
                              <span className="ml-2 text-xs text-[hsl(var(--muted-foreground))]">
                                (estándar)
                              </span>
                            )}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    ))}
                  </SelectContent>
                </Select>

                {selected_template && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    {selected_template.description ?? "Sin descripción adicional."}
                  </p>
                )}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button
                onClick={handle_next}
                disabled={!selected_template_id || category_keys.length === 0}
              >
                <Eye className="mr-1.5 h-4 w-4" />
                Vista previa
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ─── Step 2: Preview ───────────────────────────────────────── */}
      {step === 2 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Eye className="h-4 w-4 text-primary-600" />
                Vista previa del consentimiento
              </CardTitle>
            </CardHeader>
            <CardContent>
              {is_loading_template_detail ? (
                <div className="space-y-3 py-4">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ) : selected_template ? (
                <ConsentPreview
                  htmlContent={selected_template.content}
                  status="draft"
                  className="mt-2"
                />
              ) : null}
            </CardContent>
          </Card>

          <div className="flex items-center justify-between">
            <Button variant="outline" onClick={handle_back} disabled={is_creating}>
              <ChevronLeft className="mr-1.5 h-4 w-4" />
              Cambiar plantilla
            </Button>
            <Button onClick={handle_create} disabled={is_creating || is_loading_template_detail}>
              {is_creating ? "Creando..." : "Crear Consentimiento"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
