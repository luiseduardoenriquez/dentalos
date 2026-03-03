"use client";

import * as React from "react";
import { Eye, EyeOff, AlertTriangle, Variable } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

// ─── Types ────────────────────────────────────────────────────────────────────

interface EmailTemplateEditorProps {
  value: string;
  onChange: (value: string) => void;
}

// ─── Variable Definitions ─────────────────────────────────────────────────────

interface TemplateVariable {
  key: string;
  label: string;
  required: boolean;
  description: string;
}

const TEMPLATE_VARIABLES: TemplateVariable[] = [
  {
    key: "{patient_name}",
    label: "Nombre del paciente",
    required: false,
    description: "Nombre completo del paciente",
  },
  {
    key: "{clinic_name}",
    label: "Nombre de la clínica",
    required: false,
    description: "Nombre del establecimiento",
  },
  {
    key: "{tracking_pixel}",
    label: "Pixel de seguimiento",
    required: true,
    description: "Necesario para medir aperturas",
  },
  {
    key: "{unsubscribe_link}",
    label: "Enlace de desuscripción",
    required: true,
    description: "Requerido legalmente en Colombia",
  },
];

const REQUIRED_VARIABLES = TEMPLATE_VARIABLES.filter((v) => v.required).map(
  (v) => v.key,
);

// ─── EmailTemplateEditor ──────────────────────────────────────────────────────

export function EmailTemplateEditor({ value, onChange }: EmailTemplateEditorProps) {
  const [showPreview, setShowPreview] = React.useState(false);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Check which required variables are missing
  const missingRequired = REQUIRED_VARIABLES.filter(
    (v) => !value.includes(v),
  );

  function insertVariable(varKey: string) {
    const textarea = textareaRef.current;
    if (!textarea) {
      onChange(value + varKey);
      return;
    }

    const start = textarea.selectionStart ?? value.length;
    const end = textarea.selectionEnd ?? value.length;
    const before = value.slice(0, start);
    const after = value.slice(end);
    const newValue = before + varKey + after;
    onChange(newValue);

    // Restore cursor position after the inserted variable
    requestAnimationFrame(() => {
      textarea.focus();
      const newPos = start + varKey.length;
      textarea.setSelectionRange(newPos, newPos);
    });
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Variable insertion buttons */}
          {TEMPLATE_VARIABLES.map((v) => (
            <button
              key={v.key}
              type="button"
              onClick={() => insertVariable(v.key)}
              title={v.description}
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-mono font-medium",
                "border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
                v.required
                  ? "border-orange-300 bg-orange-50 text-orange-700 hover:bg-orange-100 dark:border-orange-700 dark:bg-orange-900/20 dark:text-orange-300"
                  : "border-[hsl(var(--border))] bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--background))]",
              )}
            >
              <Variable className="h-3 w-3" />
              {v.key}
              {v.required && (
                <span className="text-[10px] font-sans font-semibold ml-0.5 opacity-75">
                  *
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Preview toggle */}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setShowPreview((p) => !p)}
          className="gap-1.5 shrink-0"
        >
          {showPreview ? (
            <>
              <EyeOff className="h-3.5 w-3.5" />
              Editar
            </>
          ) : (
            <>
              <Eye className="h-3.5 w-3.5" />
              Vista previa
            </>
          )}
        </Button>
      </div>

      {/* Missing required variables warning */}
      {missingRequired.length > 0 && value.trim().length > 0 && (
        <div className="flex items-start gap-2 rounded-md border border-orange-300 bg-orange-50 dark:bg-orange-900/20 dark:border-orange-700 px-3 py-2">
          <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-orange-800 dark:text-orange-200">
              Variables requeridas faltantes
            </p>
            <p className="text-xs text-orange-700 dark:text-orange-300 mt-0.5">
              El contenido debe incluir:{" "}
              {missingRequired.map((v, i) => (
                <React.Fragment key={v}>
                  <code className="font-mono">{v}</code>
                  {i < missingRequired.length - 1 && ", "}
                </React.Fragment>
              ))}
            </p>
          </div>
        </div>
      )}

      {/* Editor or Preview */}
      {showPreview ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Vista previa del HTML — las variables aparecerán con sus nombres literales.
          </p>
          <div
            className={cn(
              "rounded-md border border-[hsl(var(--border))] bg-white text-black",
              "min-h-48 overflow-auto p-4",
            )}
            // Admin-authored HTML preview
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: value || "<p style='color:#999'>Sin contenido aún...</p>",
            }}
          />
        </div>
      ) : (
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={14}
          placeholder={`<!DOCTYPE html>
<html>
<body>
  <p>Hola {patient_name},</p>
  <p>Te escribimos desde {clinic_name}...</p>

  {tracking_pixel}
  <a href="{unsubscribe_link}">Desuscribirme</a>
</body>
</html>`}
          className="font-mono text-xs resize-y focus-visible:ring-primary-600"
          spellCheck={false}
          aria-label="Editor HTML de la plantilla de email"
        />
      )}

      {/* Footer hint */}
      <p className="text-xs text-[hsl(var(--muted-foreground))]">
        <span className="font-semibold text-orange-700 dark:text-orange-400">*</span>{" "}
        Las variables marcadas con asterisco son requeridas para el correcto funcionamiento
        del sistema de tracking y cumplimiento legal.
      </p>
    </div>
  );
}
