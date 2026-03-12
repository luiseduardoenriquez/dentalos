"use client";

import React from "react";
import {
  useGlobalTemplates,
  useUpdateGlobalTemplate,
  type GlobalTemplateItem,
} from "@/lib/hooks/use-admin";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Constants ─────────────────────────────────────────────────────────────────

const FILTER_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "consent", label: "Consentimiento" },
  { value: "evolution", label: "Evolución" },
] as const;

const TYPE_LABELS: Record<string, string> = {
  consent: "Consentimiento",
  evolution: "Evolución",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function truncate(text: string | null, max: number): string {
  if (!text) return "—";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

// ─── Template Type Badge ──────────────────────────────────────────────────────

function TemplateTypeBadge({ templateType }: { templateType: string }) {
  if (templateType === "consent") {
    return (
      <span className="inline-flex items-center rounded-full border border-blue-300 bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300">
        {TYPE_LABELS[templateType] ?? templateType}
      </span>
    );
  }

  if (templateType === "evolution") {
    return (
      <span className="inline-flex items-center rounded-full border border-green-300 bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300">
        {TYPE_LABELS[templateType] ?? templateType}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center rounded-full border border-slate-300 bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400">
      {TYPE_LABELS[templateType] ?? templateType}
    </span>
  );
}

// ─── Version Badge ─────────────────────────────────────────────────────────────

function VersionBadge({ version }: { version: number }) {
  return (
    <span className="inline-flex items-center rounded-full border border-indigo-300 bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:border-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
      v{version}
    </span>
  );
}

// ─── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ isActive }: { isActive: boolean }) {
  if (isActive) {
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
        Activo
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
      Inactivo
    </span>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function TemplatesLoadingSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
      <div className="divide-y divide-[hsl(var(--border))]">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-4 px-6 py-4">
            <div className="h-4 w-48 animate-pulse rounded bg-[hsl(var(--muted))]" />
            <div className="h-5 w-24 animate-pulse rounded-full bg-[hsl(var(--muted))]" />
            <div className="h-4 w-20 animate-pulse rounded bg-[hsl(var(--muted))]" />
            <div className="h-5 w-10 animate-pulse rounded-full bg-[hsl(var(--muted))]" />
            <div className="h-5 w-16 animate-pulse rounded-full bg-[hsl(var(--muted))]" />
            <div className="ml-auto h-8 w-16 animate-pulse rounded bg-[hsl(var(--muted))]" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Edit Template Dialog ─────────────────────────────────────────────────────

interface EditTemplateDialogProps {
  template: GlobalTemplateItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface EditFormState {
  name: string;
  is_active: boolean;
}

function EditTemplateDialog({
  template,
  open,
  onOpenChange,
}: EditTemplateDialogProps) {
  const { success, error } = useToast();
  const updateTemplate = useUpdateGlobalTemplate();

  const [form, setForm] = React.useState<EditFormState>({
    name: template.name,
    is_active: template.is_active,
  });

  // Sync form when dialog opens with a (potentially different) template
  React.useEffect(() => {
    if (open) {
      setForm({
        name: template.name,
        is_active: template.is_active,
      });
    }
  }, [open, template]);

  function handleSave() {
    if (!form.name.trim()) return;

    updateTemplate.mutate(
      {
        templateId: template.id,
        templateType: template.template_type,
        data: {
          name: form.name.trim(),
          is_active: form.is_active,
        },
      },
      {
        onSuccess: () => {
          success(
            "Plantilla actualizada",
            "Los cambios se guardaron correctamente.",
          );
          onOpenChange(false);
        },
        onError: () => {
          error(
            "Error al guardar",
            "No se pudo actualizar la plantilla. Intenta de nuevo.",
          );
        },
      },
    );
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-template-dialog-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Dialog panel */}
      <div className="relative z-10 w-full max-w-md rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 shadow-xl">
        {/* Header */}
        <div className="mb-4">
          <h2
            id="edit-template-dialog-title"
            className="text-lg font-semibold tracking-tight"
          >
            Editar plantilla
          </h2>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Modifica el nombre y el estado de la plantilla global.
          </p>
        </div>

        {/* Form */}
        <div className="space-y-4">
          {/* Nombre */}
          <div className="space-y-1.5">
            <label
              htmlFor="template-name"
              className="text-sm font-medium leading-none"
            >
              Nombre <span className="text-red-500">*</span>
            </label>
            <input
              id="template-name"
              type="text"
              value={form.name}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, name: e.target.value }))
              }
              placeholder="Nombre de la plantilla"
              className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground shadow-sm placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Tipo (read-only) */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium leading-none">Tipo</p>
            <div className="flex items-center gap-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-3 py-2">
              <TemplateTypeBadge templateType={template.template_type} />
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                No modificable
              </span>
            </div>
          </div>

          {/* Estado activo */}
          <div className="flex items-center gap-3">
            <button
              id="template-is-active"
              role="checkbox"
              aria-checked={form.is_active}
              onClick={() =>
                setForm((prev) => ({ ...prev, is_active: !prev.is_active }))
              }
              className={`relative inline-flex h-5 w-5 shrink-0 cursor-pointer items-center justify-center rounded border focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 ${
                form.is_active
                  ? "border-indigo-600 bg-indigo-600 dark:border-indigo-500 dark:bg-indigo-500"
                  : "border-[hsl(var(--border))] bg-[hsl(var(--background))]"
              }`}
            >
              {form.is_active && (
                <svg
                  className="h-3 w-3 text-white"
                  viewBox="0 0 12 12"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="2,6 5,9 10,3" />
                </svg>
              )}
            </button>
            <label
              htmlFor="template-is-active"
              className="cursor-pointer select-none text-sm font-medium"
              onClick={() =>
                setForm((prev) => ({ ...prev, is_active: !prev.is_active }))
              }
            >
              Plantilla activa
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={updateTemplate.isPending}
            className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-[hsl(var(--muted))] focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={updateTemplate.isPending || !form.name.trim()}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
          >
            {updateTemplate.isPending ? "Guardando..." : "Guardar cambios"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TemplatesPage() {
  const [activeFilter, setActiveFilter] = React.useState<string>("");
  const [editingTemplate, setEditingTemplate] =
    React.useState<GlobalTemplateItem | null>(null);

  const { data, isLoading, isError, refetch } = useGlobalTemplates(
    activeFilter || undefined,
  );

  const templates = data?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Plantillas Globales
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Gestiona plantillas de consentimiento y evolución disponibles para
            todas las clínicas.
          </p>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
          Filtrar por tipo:
        </span>
        <div className="flex items-center gap-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-1">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setActiveFilter(opt.value)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 ${
                activeFilter === opt.value
                  ? "bg-indigo-600 text-white shadow-sm dark:bg-indigo-500"
                  : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] hover:text-foreground"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && <TemplatesLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] py-12 text-center">
          <svg
            className="h-8 w-8 text-[hsl(var(--muted-foreground))]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Error al cargar las plantillas. Verifica la conexión con la API.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-1.5 text-sm font-medium hover:bg-[hsl(var(--muted))] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Templates table */}
      {!isLoading && !isError && (
        <>
          {templates.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] py-16 text-center">
              <svg
                className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-40"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No hay plantillas disponibles para el filtro seleccionado.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
              {/* Card header */}
              <div className="border-b border-[hsl(var(--border))] px-6 py-4">
                <p className="text-sm font-medium">
                  {data?.total ?? templates.length}{" "}
                  {(data?.total ?? templates.length) === 1
                    ? "plantilla en total"
                    : "plantillas en total"}
                </p>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--muted))]/40">
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                        Nombre
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                        Tipo
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                        Categoría
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                        Versión
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                        Clínicas con override
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                        Estado
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                        Acciones
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[hsl(var(--border))]">
                    {templates.map((template) => (
                      <tr
                        key={template.id}
                        className="transition-colors hover:bg-[hsl(var(--muted))]/30"
                      >
                        {/* Nombre */}
                        <td className="max-w-[240px] px-6 py-4">
                          <p
                            className="font-medium text-foreground"
                            title={template.name}
                          >
                            {truncate(template.name, 50)}
                          </p>
                        </td>

                        {/* Tipo */}
                        <td className="whitespace-nowrap px-4 py-4">
                          <TemplateTypeBadge
                            templateType={template.template_type}
                          />
                        </td>

                        {/* Categoria */}
                        <td className="whitespace-nowrap px-4 py-4 text-[hsl(var(--muted-foreground))]">
                          {template.category ?? "—"}
                        </td>

                        {/* Version */}
                        <td className="whitespace-nowrap px-4 py-4">
                          <VersionBadge version={template.version} />
                        </td>

                        {/* Tenant override count */}
                        <td className="whitespace-nowrap px-4 py-4 text-[hsl(var(--muted-foreground))]">
                          {template.tenant_override_count > 0 ? (
                            <span className="font-medium text-amber-600 dark:text-amber-400">
                              {template.tenant_override_count}
                            </span>
                          ) : (
                            <span>0</span>
                          )}
                        </td>

                        {/* Estado */}
                        <td className="whitespace-nowrap px-4 py-4">
                          <StatusBadge isActive={template.is_active} />
                        </td>

                        {/* Acciones */}
                        <td className="whitespace-nowrap px-6 py-4 text-right">
                          <button
                            type="button"
                            onClick={() => setEditingTemplate(template)}
                            className="inline-flex items-center gap-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-1.5 text-xs font-medium text-foreground shadow-sm hover:bg-[hsl(var(--muted))] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1"
                          >
                            <svg
                              className="h-3.5 w-3.5"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
                              />
                            </svg>
                            Editar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Edit dialog — only mounted when a template is selected */}
      {editingTemplate && (
        <EditTemplateDialog
          template={editingTemplate}
          open={editingTemplate !== null}
          onOpenChange={(open) => {
            if (!open) setEditingTemplate(null);
          }}
        />
      )}
    </div>
  );
}
