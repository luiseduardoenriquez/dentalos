"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FilePlus, AlertCircle } from "lucide-react";
import { apiGet } from "@/lib/api-client";
import {
  PostopTemplateList,
} from "@/components/postop/PostopTemplateList";
import {
  PostopTemplateForm,
  type PostopTemplate,
} from "@/components/postop/PostopTemplateForm";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PostopTemplatesResponse {
  items: PostopTemplate[];
  total: number;
}

// ─── Query key ────────────────────────────────────────────────────────────────

const POSTOP_TEMPLATES_KEY = ["postop-templates"] as const;

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-8 w-64 rounded bg-slate-200 dark:bg-zinc-700" />
        <div className="h-9 w-44 rounded bg-slate-200 dark:bg-zinc-700" />
      </div>
      <div className="rounded-xl border border-[hsl(var(--border))] overflow-hidden">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="flex items-center gap-4 px-4 py-3 border-b last:border-0"
          >
            <div className="h-4 w-28 rounded bg-slate-100 dark:bg-zinc-800" />
            <div className="h-4 w-48 rounded bg-slate-100 dark:bg-zinc-800" />
            <div className="h-5 w-16 rounded-full bg-slate-100 dark:bg-zinc-800" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * /settings/postop-templates
 *
 * Manage post-operative instruction templates.
 * clinic_owner and doctors can create, edit, and deactivate templates.
 */
export default function PostopTemplatesPage() {
  const [mode, setMode] = React.useState<"list" | "create" | "edit">("list");
  const [editTarget, setEditTarget] = React.useState<PostopTemplate | null>(
    null,
  );

  const { data, isLoading, isError } = useQuery({
    queryKey: POSTOP_TEMPLATES_KEY,
    queryFn: () => apiGet<PostopTemplatesResponse>("/postop/templates"),
    staleTime: 60_000,
  });

  const templates = data?.items ?? [];

  function handleEdit(template: PostopTemplate) {
    setEditTarget(template);
    setMode("edit");
  }

  function handleFormSuccess() {
    setMode("list");
    setEditTarget(null);
  }

  function handleCancel() {
    setMode("list");
    setEditTarget(null);
  }

  // ─── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) return <PageSkeleton />;

  // ─── Error ──────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          Error al cargar las plantillas
        </p>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          No se pudieron obtener las plantillas post-operatorias. Recarga la
          página.
        </p>
      </div>
    );
  }

  // ─── Create / Edit form ──────────────────────────────────────────────────────
  if (mode === "create" || mode === "edit") {
    return (
      <div className="max-w-2xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[hsl(var(--foreground))]">
            {mode === "create" ? "Nueva plantilla post-op" : "Editar plantilla"}
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            {mode === "create"
              ? "Crea una plantilla de instrucciones para enviar a los pacientes después de un procedimiento."
              : "Modifica las instrucciones o configuración de esta plantilla."}
          </p>
        </div>

        {/* Divider */}
        <div className="border-t border-[hsl(var(--border))]" />

        {/* Form */}
        <PostopTemplateForm
          template={editTarget ?? undefined}
          onSuccess={handleFormSuccess}
          onCancel={handleCancel}
        />
      </div>
    );
  }

  // ─── List view ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[hsl(var(--foreground))]">
            Plantillas post-operatorias
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Define las instrucciones que se envían automáticamente al paciente
            después de cada procedimiento.
          </p>
        </div>

        <button
          onClick={() => setMode("create")}
          className="inline-flex items-center gap-2 self-start sm:self-auto rounded-lg bg-teal-600 text-white px-4 py-2.5 text-sm font-medium hover:bg-teal-700 transition-colors"
        >
          <FilePlus className="h-4 w-4" />
          Nueva plantilla
        </button>
      </div>

      {/* Stats summary */}
      {templates.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatPill
            label="Total"
            value={templates.length}
          />
          <StatPill
            label="Activas"
            value={templates.filter((t) => t.is_active).length}
          />
          <StatPill
            label="Por defecto"
            value={templates.filter((t) => t.is_default).length}
          />
        </div>
      )}

      {/* Template list */}
      <PostopTemplateList
        templates={templates.filter((t) => t.is_active)}
        onEdit={handleEdit}
      />

      {/* Inactive templates section */}
      {templates.some((t) => !t.is_active) && (
        <details className="group">
          <summary className="cursor-pointer text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors">
            Ver plantillas inactivas (
            {templates.filter((t) => !t.is_active).length})
          </summary>
          <div className="mt-3">
            <PostopTemplateList
              templates={templates.filter((t) => !t.is_active)}
              onEdit={handleEdit}
            />
          </div>
        </details>
      )}
    </div>
  );
}

// ─── Stat pill ────────────────────────────────────────────────────────────────

function StatPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-4 py-3 text-center">
      <p className="text-2xl font-bold text-[hsl(var(--foreground))]">
        {value}
      </p>
      <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
        {label}
      </p>
    </div>
  );
}
