"use client";

import * as React from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
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
import { ProcedureForm } from "@/components/procedure-form";

const RichTextEditor = dynamic(
  () => import("@/components/rich-text-editor").then(m => ({ default: m.RichTextEditor })),
  { ssr: false, loading: () => <div className="h-[200px] rounded-md border animate-pulse" /> }
);
import {
  useCreateClinicalRecord,
  useEvolutionTemplates,
} from "@/lib/hooks/use-clinical-records";
import { cn } from "@/lib/utils";
import { DictateClinicalNoteButton } from "@/components/voice/dictate-clinical-note-button";

// ─── Types ───────────────────────────────────────────────────────────────────

type RecordType = "examination" | "evolution_note" | "procedure";

const TYPE_OPTIONS: { value: RecordType; label: string; description: string }[] = [
  {
    value: "examination",
    label: "Examen",
    description: "Examen clínico general o hallazgo.",
  },
  {
    value: "evolution_note",
    label: "Nota de evolución",
    description: "Nota clínica basada en plantilla de evolución.",
  },
  {
    value: "procedure",
    label: "Procedimiento",
    description: "Registro de procedimiento con código CUPS.",
  },
];

// ─── Tooth Number Input ──────────────────────────────────────────────────────

function ToothNumbersInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor="tooth_numbers">
        Diente(s){" "}
        <span className="text-xs text-[hsl(var(--muted-foreground))] font-normal">
          (separados por coma, FDI: 11-85)
        </span>
      </Label>
      <Input
        id="tooth_numbers"
        placeholder="ej: 11, 21, 36"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function NewClinicalRecordPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;

  const [recordType, setRecordType] = React.useState<RecordType>("examination");
  const [htmlContent, setHtmlContent] = React.useState("");
  const [toothNumbers, setToothNumbers] = React.useState("");
  const [selectedTemplateId, setSelectedTemplateId] = React.useState("");

  const { mutate: createRecord, isPending } = useCreateClinicalRecord(patientId);
  const { data: templatesData } = useEvolutionTemplates();
  const templates = templatesData?.items ?? [];

  // Pre-fill editor when a template is selected
  React.useEffect(() => {
    if (!selectedTemplateId) return;
    const template = templates.find((t) => t.id === selectedTemplateId);
    if (template) {
      // Build content from template name as starting point
      setHtmlContent(`<h2>${template.name}</h2><p></p>`);
    }
  }, [selectedTemplateId, templates]);

  function parseToothNumbers(): number[] | null {
    if (!toothNumbers.trim()) return null;
    const nums = toothNumbers
      .split(",")
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n >= 11 && n <= 85);
    return nums.length > 0 ? nums : null;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!htmlContent.trim() || htmlContent === "<p></p>") return;

    createRecord(
      {
        type: recordType,
        content: { html: htmlContent },
        tooth_numbers: parseToothNumbers(),
        template_id: selectedTemplateId || null,
      },
      {
        onSuccess: () => {
          router.push(`/patients/${patientId}/clinical-records`);
        },
      },
    );
  }

  function handleProcedureSuccess() {
    router.push(`/patients/${patientId}/clinical-records`);
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
          href={`/patients/${patientId}`}
          className="hover:text-foreground transition-colors"
        >
          Detalle del paciente
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}/clinical-records`}
          className="hover:text-foreground transition-colors"
        >
          Registros clínicos
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nuevo registro</span>
      </nav>

      {/* ─── Page Title ──────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Nuevo registro clínico
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Selecciona el tipo de registro y completa la información.
        </p>
      </div>

      {/* ─── AI Dictation (evolution notes) ──────────────────────────────── */}
      {recordType === "evolution_note" && (
        <Card>
          <CardContent className="flex items-center justify-between py-3">
            <div>
              <p className="text-sm font-medium text-foreground">Dictado con IA</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Dicta tu nota y la IA la estructura en formato SOAP automáticamente.
              </p>
            </div>
            <DictateClinicalNoteButton patientId={patientId} />
          </CardContent>
        </Card>
      )}

      {/* ─── Type Selector ───────────────────────────────────────────────── */}
      <div className="flex gap-2">
        {TYPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => {
              setRecordType(opt.value);
              setHtmlContent("");
              setSelectedTemplateId("");
            }}
            className={cn(
              "flex-1 rounded-lg border px-4 py-3 text-left transition-colors",
              recordType === opt.value
                ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                : "border-[hsl(var(--border))] hover:border-primary-300",
            )}
          >
            <p
              className={cn(
                "text-sm font-semibold",
                recordType === opt.value ? "text-primary-700 dark:text-primary-300" : "text-foreground",
              )}
            >
              {opt.label}
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
              {opt.description}
            </p>
          </button>
        ))}
      </div>

      {/* ─── Procedure Type (delegates to ProcedureForm) ─────────────────── */}
      {recordType === "procedure" && (
        <ProcedureForm patientId={patientId} onSuccess={handleProcedureSuccess} />
      )}

      {/* ─── Examination & Evolution Note Forms ──────────────────────────── */}
      {recordType !== "procedure" && (
        <form onSubmit={handleSubmit} noValidate className="space-y-6">
          {/* Template selector for evolution notes */}
          {recordType === "evolution_note" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Plantilla de evolución</CardTitle>
                <CardDescription>
                  Selecciona una plantilla para precargar el contenido.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Select
                  value={selectedTemplateId}
                  onValueChange={setSelectedTemplateId}
                >
                  <SelectTrigger aria-label="Seleccionar plantilla de evolución">
                    <SelectValue placeholder="Selecciona una plantilla (opcional)..." />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                        {t.is_builtin && (
                          <span className="ml-2 text-xs text-[hsl(var(--muted-foreground))]">
                            (estándar)
                          </span>
                        )}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>
          )}

          {/* Content editor */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {recordType === "examination" ? "Contenido del examen" : "Nota de evolución"}
              </CardTitle>
              <CardDescription>
                {recordType === "examination"
                  ? "Registra los hallazgos del examen clínico."
                  : "Escribe la nota de evolución del paciente."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <RichTextEditor
                content={htmlContent}
                onChange={setHtmlContent}
                placeholder={
                  recordType === "examination"
                    ? "Describe los hallazgos del examen..."
                    : "Escribe la nota de evolución..."
                }
                minHeight="250px"
              />

              <ToothNumbersInput value={toothNumbers} onChange={setToothNumbers} />
            </CardContent>
          </Card>

          {/* ─── Action Buttons ──────────────────────────────────────────── */}
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" asChild>
              <Link href={`/patients/${patientId}/clinical-records`}>Cancelar</Link>
            </Button>
            <Button
              type="submit"
              disabled={isPending || !htmlContent.trim() || htmlContent === "<p></p>"}
            >
              {isPending ? "Guardando..." : "Crear registro"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
