"use client";

import * as React from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { ChevronRight, Eye, EyeOff } from "lucide-react";
import { type Editor } from "@tiptap/react";
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
import { ConsentPreview } from "@/components/consent-preview";

const RichTextEditor = dynamic(
  () => import("@/components/rich-text-editor").then(m => ({ default: m.RichTextEditor })),
  { ssr: false, loading: () => <div className="h-[400px] rounded-md border animate-pulse" /> }
);
import { useCreateConsentTemplate } from "@/lib/hooks/use-consent-templates";
import { cn } from "@/lib/utils";

// ─── Category Options ────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "surgery", label: "Cirugía" },
  { value: "sedation", label: "Sedación" },
  { value: "orthodontics", label: "Ortodoncia" },
  { value: "implants", label: "Implantes" },
  { value: "endodontics", label: "Endodoncia" },
  { value: "pediatric", label: "Pediátrico" },
];

// ─── Template Variables ──────────────────────────────────────────────────────

const TEMPLATE_VARIABLES = [
  { key: "{{patient_name}}", label: "Nombre paciente" },
  { key: "{{patient_document}}", label: "Documento" },
  { key: "{{date}}", label: "Fecha" },
  { key: "{{procedure}}", label: "Procedimiento" },
  { key: "{{doctor_name}}", label: "Nombre doctor" },
];

// ─── Page ────────────────────────────────────────────────────────────────────

export default function NewConsentTemplatePage() {
  const router = useRouter();

  const [name, setName] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [htmlContent, setHtmlContent] = React.useState("");
  const [showPreview, setShowPreview] = React.useState(false);
  const editorRef = React.useRef<Editor | null>(null);

  const { mutate: createTemplate, isPending } = useCreateConsentTemplate();

  async function handleVariableInsert(variable: string) {
    const { insertTextAtCursor } = await import("@/components/rich-text-editor");
    insertTextAtCursor(editorRef.current, variable);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !category || !htmlContent.trim()) return;

    createTemplate(
      {
        name: name.trim(),
        category,
        description: description.trim() || null,
        content: htmlContent,
      },
      {
        onSuccess: () => {
          router.push("/settings/consent-templates");
        },
      },
    );
  }

  const canSubmit = name.trim() && category && htmlContent.trim() && htmlContent !== "<p></p>";

  return (
    <div className="max-w-4xl space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/settings" className="hover:text-foreground transition-colors">
          Configuración
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href="/settings/consent-templates"
          className="hover:text-foreground transition-colors"
        >
          Plantillas de consentimiento
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nueva plantilla</span>
      </nav>

      {/* ─── Page Title ──────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Nueva plantilla de consentimiento
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Crea una plantilla personalizada para consentimientos informados.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* ─── Metadata ──────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Información básica</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="name">
                  Nombre <span className="text-destructive-600">*</span>
                </Label>
                <Input
                  id="name"
                  placeholder="ej: Consentimiento para extracción"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={isPending}
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="category">
                  Categoría <span className="text-destructive-600">*</span>
                </Label>
                <Select value={category} onValueChange={setCategory} disabled={isPending}>
                  <SelectTrigger id="category" aria-label="Categoría">
                    <SelectValue placeholder="Selecciona categoría" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1">
              <Label htmlFor="description">
                Descripción{" "}
                <span className="text-xs text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </Label>
              <textarea
                id="description"
                rows={2}
                placeholder="Descripción breve de la plantilla..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isPending}
                className={cn(
                  "flex w-full rounded-md border border-[hsl(var(--input))] bg-transparent px-3 py-2 text-sm shadow-sm",
                  "placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-600",
                  "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
                )}
              />
            </div>
          </CardContent>
        </Card>

        {/* ─── Content Editor ────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Contenido del consentimiento</CardTitle>
                <CardDescription>
                  Usa las variables para personalizar el contenido automáticamente.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowPreview((prev) => !prev)}
              >
                {showPreview ? (
                  <>
                    <EyeOff className="mr-1.5 h-3.5 w-3.5" />
                    Editor
                  </>
                ) : (
                  <>
                    <Eye className="mr-1.5 h-3.5 w-3.5" />
                    Vista previa
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Variable chips */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-[hsl(var(--muted-foreground))] mr-1">
                Variables:
              </span>
              {TEMPLATE_VARIABLES.map((v) => (
                <button
                  key={v.key}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleVariableInsert(v.key);
                  }}
                  disabled={isPending || showPreview}
                  className={cn(
                    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-mono",
                    "border border-[hsl(var(--border))] bg-[hsl(var(--muted))]",
                    "hover:bg-primary-100 hover:border-primary-300 hover:text-primary-700",
                    "dark:hover:bg-primary-900/30 dark:hover:text-primary-300",
                    "transition-colors cursor-pointer",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                  )}
                  title={`Insertar ${v.label}`}
                >
                  {v.label}
                </button>
              ))}
            </div>

            {/* Editor or Preview */}
            {showPreview ? (
              <ConsentPreview
                htmlContent={htmlContent || "<p><em>Sin contenido aún.</em></p>"}
                status="draft"
              />
            ) : (
              <RichTextEditor
                content={htmlContent}
                onChange={setHtmlContent}
                editable={!isPending}
                placeholder="Escribe el contenido del consentimiento informado..."
                minHeight="400px"
                onEditorReady={(e) => {
                  editorRef.current = e;
                }}
              />
            )}
          </CardContent>
        </Card>

        {/* ─── Action Buttons ────────────────────────────────────────────── */}
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" asChild>
            <Link href="/settings/consent-templates">Cancelar</Link>
          </Button>
          <Button type="submit" disabled={isPending || !canSubmit}>
            {isPending ? "Creando..." : "Crear plantilla"}
          </Button>
        </div>
      </form>
    </div>
  );
}
