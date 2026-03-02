"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save } from "lucide-react";
import { apiPost, apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PostopTemplate {
  id: string;
  procedure_type: string;
  title: string;
  instruction_content: string;
  channel_preference: "whatsapp" | "email" | "portal" | "all";
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PostopTemplateFormValues {
  procedure_type: string;
  title: string;
  instruction_content: string;
  channel_preference: "whatsapp" | "email" | "portal" | "all";
  is_default: boolean;
}

interface PostopTemplateFormProps {
  /** When provided, the form is in edit mode. */
  template?: PostopTemplate;
  onSuccess?: (template: PostopTemplate) => void;
  onCancel?: () => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PROCEDURE_TYPES = [
  { value: "resina", label: "Resina / Composite" },
  { value: "endodoncia", label: "Endodoncia" },
  { value: "exodoncia", label: "Exodoncia" },
  { value: "profilaxis", label: "Profilaxis / Limpieza" },
  { value: "implante", label: "Implante" },
  { value: "cirugia_periodontal", label: "Cirugía periodontal" },
  { value: "corona", label: "Corona / Prótesis" },
  { value: "ortodoncia", label: "Ortodoncia (brackets)" },
  { value: "blanqueamiento", label: "Blanqueamiento" },
  { value: "sedacion", label: "Sedación" },
  { value: "otro", label: "Otro" },
] as const;

const CHANNEL_OPTIONS = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "email", label: "Correo electrónico" },
  { value: "portal", label: "Portal del paciente" },
  { value: "all", label: "Todos los canales" },
] as const;

const POSTOP_TEMPLATES_KEY = ["postop-templates"] as const;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Form for creating or editing a post-operative instruction template.
 *
 * POST /postop/templates        — create
 * PUT  /postop/templates/{id}  — update
 */
export function PostopTemplateForm({
  template,
  onSuccess,
  onCancel,
}: PostopTemplateFormProps) {
  const queryClient = useQueryClient();
  const { success, error: toastError } = useToast();

  const isEdit = Boolean(template);

  const [values, setValues] = React.useState<PostopTemplateFormValues>({
    procedure_type: template?.procedure_type ?? "resina",
    title: template?.title ?? "",
    instruction_content: template?.instruction_content ?? "",
    channel_preference: template?.channel_preference ?? "all",
    is_default: template?.is_default ?? false,
  });

  const [errors, setErrors] = React.useState<Partial<Record<keyof PostopTemplateFormValues, string>>>({});

  // ─── Mutation ──────────────────────────────────────────────────────────────
  const { mutate, isPending } = useMutation({
    mutationFn: (data: PostopTemplateFormValues) =>
      isEdit
        ? apiClient
            .put<PostopTemplate>(`/postop/templates/${template!.id}`, data)
            .then((r) => r.data)
        : apiPost<PostopTemplate>("/postop/templates", data),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: POSTOP_TEMPLATES_KEY });
      success(
        isEdit ? "Plantilla actualizada" : "Plantilla creada",
        isEdit
          ? "Los cambios fueron guardados."
          : "La plantilla fue creada exitosamente.",
      );
      onSuccess?.(saved);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo guardar la plantilla.";
      toastError("Error al guardar", message);
    },
  });

  // ─── Validation ────────────────────────────────────────────────────────────
  function validate(): boolean {
    const next: typeof errors = {};
    if (!values.procedure_type) next.procedure_type = "Selecciona el tipo de procedimiento.";
    if (!values.title.trim()) next.title = "El título es obligatorio.";
    if (!values.instruction_content.trim())
      next.instruction_content = "Las instrucciones no pueden estar vacías.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    mutate(values);
  }

  function set<K extends keyof PostopTemplateFormValues>(
    key: K,
    value: PostopTemplateFormValues[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {/* Procedure type */}
      <div>
        <label
          htmlFor="procedure_type"
          className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5"
        >
          Tipo de procedimiento
        </label>
        <select
          id="procedure_type"
          value={values.procedure_type}
          onChange={(e) => set("procedure_type", e.target.value)}
          className="w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          {PROCEDURE_TYPES.map((pt) => (
            <option key={pt.value} value={pt.value}>
              {pt.label}
            </option>
          ))}
        </select>
        {errors.procedure_type && (
          <p className="mt-1 text-xs text-red-500">{errors.procedure_type}</p>
        )}
      </div>

      {/* Title */}
      <div>
        <label
          htmlFor="title"
          className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5"
        >
          Título de la plantilla
        </label>
        <input
          id="title"
          type="text"
          value={values.title}
          onChange={(e) => set("title", e.target.value)}
          placeholder="Ej: Cuidados post-extracción dental"
          className="w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        {errors.title && (
          <p className="mt-1 text-xs text-red-500">{errors.title}</p>
        )}
      </div>

      {/* Instruction content */}
      <div>
        <label
          htmlFor="instruction_content"
          className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5"
        >
          Instrucciones para el paciente
        </label>
        <textarea
          id="instruction_content"
          rows={8}
          value={values.instruction_content}
          onChange={(e) => set("instruction_content", e.target.value)}
          placeholder="Escribe aquí las instrucciones detalladas que recibirá el paciente después del procedimiento..."
          className="w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] px-3 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
        <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
          {values.instruction_content.length} caracteres
        </p>
        {errors.instruction_content && (
          <p className="mt-1 text-xs text-red-500">
            {errors.instruction_content}
          </p>
        )}
      </div>

      {/* Channel preference */}
      <div>
        <label
          htmlFor="channel_preference"
          className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1.5"
        >
          Canal de envío
        </label>
        <select
          id="channel_preference"
          value={values.channel_preference}
          onChange={(e) =>
            set(
              "channel_preference",
              e.target.value as PostopTemplateFormValues["channel_preference"],
            )
          }
          className="w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          {CHANNEL_OPTIONS.map((ch) => (
            <option key={ch.value} value={ch.value}>
              {ch.label}
            </option>
          ))}
        </select>
      </div>

      {/* Is default */}
      <div className="flex items-start gap-3">
        <input
          id="is_default"
          type="checkbox"
          checked={values.is_default}
          onChange={(e) => set("is_default", e.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
        />
        <div>
          <label
            htmlFor="is_default"
            className="text-sm font-medium text-[hsl(var(--foreground))]"
          >
            Plantilla predeterminada
          </label>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Se usará automáticamente cuando se registre este tipo de
            procedimiento.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 text-white px-5 py-2.5 text-sm font-medium hover:bg-teal-700 disabled:opacity-60 transition-colors"
        >
          {isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {isPending ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear plantilla"}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="text-sm text-[hsl(var(--muted-foreground))] hover:underline disabled:opacity-50 transition-colors"
          >
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}
