"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, RefreshCw } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentFilterBuilder } from "@/components/marketing/segment-filter-builder";
import { EmailTemplateEditor } from "@/components/marketing/email-template-editor";
import type { SegmentFilters } from "@/components/marketing/segment-filter-builder";
import type { EmailCampaign } from "@/app/(dashboard)/marketing/page";

// ─── Types ────────────────────────────────────────────────────────────────────

interface EmailTemplate {
  id: string;
  name: string;
  description: string | null;
  subject: string;
  html_body: string;
  category: string;
  preview_image_url: string | null;
}

interface TemplateListResponse {
  items: EmailTemplate[];
  total: number;
}

interface CampaignCreatePayload {
  name: string;
  subject: string;
  html_body: string;
  template_id: string | null;
  segment_filters: SegmentFilters;
  scheduled_at: string | null;
}

// ─── Wizard Steps ─────────────────────────────────────────────────────────────

type WizardStep = "template" | "details" | "segment" | "preview";

const STEPS: { key: WizardStep; label: string }[] = [
  { key: "template", label: "Plantilla" },
  { key: "details", label: "Contenido" },
  { key: "segment", label: "Audiencia" },
  { key: "preview", label: "Vista previa" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewCampaignPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  const [step, setStep] = React.useState<WizardStep>("template");
  const [selectedTemplateId, setSelectedTemplateId] = React.useState<string | null>(null);
  const [name, setName] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [htmlBody, setHtmlBody] = React.useState("");
  const [segmentFilters, setSegmentFilters] = React.useState<SegmentFilters>({});
  const [scheduledAt, setScheduledAt] = React.useState("");

  // Load templates
  const { data: templatesData, isLoading: isLoadingTemplates } = useQuery({
    queryKey: ["email-templates"],
    queryFn: () => apiGet<TemplateListResponse>("/marketing/templates"),
    staleTime: 5 * 60_000,
  });

  // Create campaign mutation
  const { mutate: createCampaign, isPending: isCreating } = useMutation({
    mutationFn: (payload: CampaignCreatePayload) =>
      apiPost<EmailCampaign>("/marketing/campaigns", payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["email-campaigns"] });
      success("Campaña creada", "La campaña fue guardada como borrador.");
      router.push(`/marketing/${data.id}`);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo crear la campaña.";
      error("Error al crear campaña", message);
    },
  });

  // When a template is selected, pre-fill content
  function handleSelectTemplate(template: EmailTemplate) {
    setSelectedTemplateId(template.id);
    setSubject(template.subject);
    setHtmlBody(template.html_body);
  }

  function handleSkipTemplate() {
    setSelectedTemplateId(null);
    setStep("details");
  }

  function handleSaveOrSend(send: boolean) {
    createCampaign({
      name: name.trim(),
      subject: subject.trim(),
      html_body: htmlBody,
      template_id: selectedTemplateId,
      segment_filters: segmentFilters,
      scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null,
    });
  }

  const currentStepIndex = STEPS.findIndex((s) => s.key === step);

  function goNext() {
    const nextStep = STEPS[currentStepIndex + 1];
    if (nextStep) setStep(nextStep.key);
  }

  function goPrev() {
    const prevStep = STEPS[currentStepIndex - 1];
    if (prevStep) setStep(prevStep.key);
  }

  // Validation per step
  const canGoNext = React.useMemo(() => {
    if (step === "template") return true;
    if (step === "details") return name.trim().length > 0 && subject.trim().length > 0 && htmlBody.trim().length > 0;
    if (step === "segment") return true;
    return true;
  }, [step, name, subject, htmlBody]);

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      {/* Back navigation */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/marketing")}
          className="gap-1.5 -ml-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver a campañas
        </Button>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-0">
        {STEPS.map((s, idx) => {
          const isCompleted = idx < currentStepIndex;
          const isActive = s.key === step;

          return (
            <React.Fragment key={s.key}>
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold border-2 transition-colors",
                    isCompleted
                      ? "bg-primary-600 border-primary-600 text-white"
                      : isActive
                        ? "border-primary-600 text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-900/20"
                        : "border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] bg-[hsl(var(--background))]",
                  )}
                >
                  {isCompleted ? <Check className="h-3.5 w-3.5" /> : idx + 1}
                </div>
                <span
                  className={cn(
                    "text-sm font-medium",
                    isActive
                      ? "text-foreground"
                      : "text-[hsl(var(--muted-foreground))]",
                  )}
                >
                  {s.label}
                </span>
              </div>
              {idx < STEPS.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-px mx-3",
                    idx < currentStepIndex
                      ? "bg-primary-600"
                      : "bg-[hsl(var(--border))]",
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* ── Step 1: Template selection ── */}
      {step === "template" && (
        <TemplateSelectionStep
          templates={templatesData?.items ?? []}
          isLoading={isLoadingTemplates}
          selectedId={selectedTemplateId}
          onSelect={handleSelectTemplate}
          onSkip={handleSkipTemplate}
          onNext={() => setStep("details")}
        />
      )}

      {/* ── Step 2: Campaign details ── */}
      {step === "details" && (
        <DetailsStep
          name={name}
          subject={subject}
          htmlBody={htmlBody}
          onChangeName={setName}
          onChangeSubject={setSubject}
          onChangeBody={setHtmlBody}
        />
      )}

      {/* ── Step 3: Segment filters ── */}
      {step === "segment" && (
        <SegmentStep
          filters={segmentFilters}
          onChangeFilters={setSegmentFilters}
        />
      )}

      {/* ── Step 4: Preview + send ── */}
      {step === "preview" && (
        <PreviewStep
          name={name}
          subject={subject}
          htmlBody={htmlBody}
          filters={segmentFilters}
          scheduledAt={scheduledAt}
          onChangeScheduledAt={setScheduledAt}
          onSave={() => handleSaveOrSend(false)}
          isSaving={isCreating}
        />
      )}

      {/* Navigation buttons */}
      <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))]">
        <Button
          variant="outline"
          size="sm"
          onClick={goPrev}
          disabled={currentStepIndex === 0}
          className="gap-1.5"
        >
          <ArrowLeft className="h-4 w-4" />
          Anterior
        </Button>

        {step !== "preview" ? (
          <Button
            size="sm"
            onClick={goNext}
            disabled={!canGoNext}
            className="gap-1.5"
          >
            Siguiente
            <ArrowRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={() => handleSaveOrSend(false)}
            disabled={isCreating || !name.trim() || !subject.trim() || !htmlBody.trim()}
            className="gap-1.5"
          >
            {isCreating ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <Check className="h-3.5 w-3.5" />
                Guardar como borrador
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Step Components ──────────────────────────────────────────────────────────

interface TemplateSelectionStepProps {
  templates: EmailTemplate[];
  isLoading: boolean;
  selectedId: string | null;
  onSelect: (t: EmailTemplate) => void;
  onSkip: () => void;
  onNext: () => void;
}

function TemplateSelectionStep({
  templates,
  isLoading,
  selectedId,
  onSelect,
  onSkip,
  onNext,
}: TemplateSelectionStepProps) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold">Selecciona una plantilla</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Elige una plantilla como punto de partida o empieza desde cero.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-5 w-5 animate-spin text-[hsl(var(--muted-foreground))]" />
        </div>
      )}

      {!isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Blank template option */}
          <button
            type="button"
            onClick={onSkip}
            className={cn(
              "flex flex-col items-start gap-2 rounded-lg border-2 p-4 text-left transition-colors",
              "hover:border-primary-400 focus-visible:outline-none focus-visible:border-primary-600",
              selectedId === null
                ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                : "border-[hsl(var(--border))]",
            )}
          >
            <div className="flex h-10 w-full items-center justify-center rounded-md bg-[hsl(var(--muted))]">
              <span className="text-xs text-[hsl(var(--muted-foreground))]">En blanco</span>
            </div>
            <span className="text-sm font-medium">Empezar en blanco</span>
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              Editor HTML sin plantilla
            </span>
          </button>

          {templates.map((template) => (
            <button
              key={template.id}
              type="button"
              onClick={() => {
                onSelect(template);
                onNext();
              }}
              className={cn(
                "flex flex-col items-start gap-2 rounded-lg border-2 p-4 text-left transition-colors",
                "hover:border-primary-400 focus-visible:outline-none focus-visible:border-primary-600",
                selectedId === template.id
                  ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                  : "border-[hsl(var(--border))]",
              )}
            >
              {/* Preview thumbnail */}
              <div className="flex h-10 w-full items-center justify-center rounded-md bg-[hsl(var(--muted))] overflow-hidden">
                {template.preview_image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={template.preview_image_url}
                    alt={template.name}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    Sin vista previa
                  </span>
                )}
              </div>
              <span className="text-sm font-medium">{template.name}</span>
              {template.description && (
                <span className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2">
                  {template.description}
                </span>
              )}
              <span className="text-[10px] font-medium text-primary-600 dark:text-primary-400 uppercase tracking-wide">
                {template.category}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface DetailsStepProps {
  name: string;
  subject: string;
  htmlBody: string;
  onChangeName: (v: string) => void;
  onChangeSubject: (v: string) => void;
  onChangeBody: (v: string) => void;
}

function DetailsStep({
  name,
  subject,
  htmlBody,
  onChangeName,
  onChangeSubject,
  onChangeBody,
}: DetailsStepProps) {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">Detalles de la campaña</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Define el nombre interno, asunto del email y el contenido.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="campaign-name">
            Nombre de la campaña <span className="text-red-500">*</span>
          </Label>
          <Input
            id="campaign-name"
            value={name}
            onChange={(e) => onChangeName(e.target.value)}
            placeholder="Ej: Recordatorio de limpieza — Marzo 2026"
            maxLength={255}
          />
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Nombre interno para identificar la campaña.
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="campaign-subject">
            Asunto del email <span className="text-red-500">*</span>
          </Label>
          <Input
            id="campaign-subject"
            value={subject}
            onChange={(e) => onChangeSubject(e.target.value)}
            placeholder="Ej: ¡Recuerda tu cita de revisión, {patient_name}!"
            maxLength={255}
          />
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Puedes usar {"{patient_name}"} y {"{clinic_name}"} como variables.
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>
            Contenido del email <span className="text-red-500">*</span>
          </Label>
          <EmailTemplateEditor value={htmlBody} onChange={onChangeBody} />
        </div>
      </div>
    </div>
  );
}

interface SegmentStepProps {
  filters: SegmentFilters;
  onChangeFilters: (f: SegmentFilters) => void;
}

function SegmentStep({ filters, onChangeFilters }: SegmentStepProps) {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">Audiencia objetivo</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Define los filtros de segmentación. Deja en blanco para enviar a todos los pacientes activos.
        </p>
      </div>

      <SegmentFilterBuilder filters={filters} onChange={onChangeFilters} />
    </div>
  );
}

interface PreviewStepProps {
  name: string;
  subject: string;
  htmlBody: string;
  filters: SegmentFilters;
  scheduledAt: string;
  onChangeScheduledAt: (v: string) => void;
  onSave: () => void;
  isSaving: boolean;
}

function PreviewStep({
  name,
  subject,
  htmlBody,
  filters,
  scheduledAt,
  onChangeScheduledAt,
}: PreviewStepProps) {
  const activeFilterCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== null && v !== "",
  ).length;

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">Vista previa y envío</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Revisa los detalles antes de guardar o programar el envío.
        </p>
      </div>

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resumen de campaña</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <SummaryRow label="Nombre" value={name || "—"} />
          <SummaryRow label="Asunto" value={subject || "—"} />
          <SummaryRow
            label="Segmentación"
            value={
              activeFilterCount === 0
                ? "Todos los pacientes activos"
                : `${activeFilterCount} ${activeFilterCount === 1 ? "filtro activo" : "filtros activos"}`
            }
          />
        </CardContent>
      </Card>

      {/* HTML preview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Vista previa del contenido</CardTitle>
          <CardDescription>
            Las variables como {"{patient_name}"} serán reemplazadas en el envío real.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="rounded-md border border-[hsl(var(--border))] bg-white p-4 text-black overflow-auto max-h-64"
            // Use dangerouslySetInnerHTML intentionally for email preview — content is authored by admin
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{ __html: htmlBody || "<p>Sin contenido</p>" }}
          />
        </CardContent>
      </Card>

      {/* Schedule */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Programar envío (opcional)</CardTitle>
          <CardDescription>
            Deja vacío para guardar como borrador y enviar manualmente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="scheduled-at">Fecha y hora de envío</Label>
            <input
              id="scheduled-at"
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => onChangeScheduledAt(e.target.value)}
              min={new Date().toISOString().slice(0, 16)}
              className={cn(
                "flex h-9 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
                "px-3 py-1 text-sm shadow-sm transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
              )}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3">
      <span className="text-sm text-[hsl(var(--muted-foreground))] w-28 shrink-0">
        {label}
      </span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}
