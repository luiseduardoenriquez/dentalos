"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal, Pencil, PowerOff, Star } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import type { PostopTemplate } from "@/components/postop/PostopTemplateForm";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PostopTemplateListProps {
  templates: PostopTemplate[];
  onEdit: (template: PostopTemplate) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PROCEDURE_LABELS: Record<string, string> = {
  resina: "Resina",
  endodoncia: "Endodoncia",
  exodoncia: "Exodoncia",
  profilaxis: "Profilaxis",
  implante: "Implante",
  cirugia_periodontal: "Cir. Periodontal",
  corona: "Corona",
  ortodoncia: "Ortodoncia",
  blanqueamiento: "Blanqueamiento",
  sedacion: "Sedación",
  otro: "Otro",
};

const CHANNEL_LABELS: Record<string, { label: string; color: string }> = {
  whatsapp: {
    label: "WhatsApp",
    color:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  },
  email: {
    label: "Email",
    color:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  },
  portal: {
    label: "Portal",
    color:
      "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
  },
  all: {
    label: "Todos",
    color:
      "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  },
};

const POSTOP_TEMPLATES_KEY = ["postop-templates"] as const;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Renders the list of post-operative instruction templates in a compact table.
 *
 * Each row shows: procedure type, title, channel badge, default indicator,
 * and an actions dropdown (edit / deactivate).
 */
export function PostopTemplateList({
  templates,
  onEdit,
}: PostopTemplateListProps) {
  const queryClient = useQueryClient();
  const { success, error: toastError } = useToast();
  const [openMenuId, setOpenMenuId] = React.useState<string | null>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);

  // ─── Close menu on outside click ──────────────────────────────────────────
  React.useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenuId(null);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // ─── Deactivate mutation ───────────────────────────────────────────────────
  const { mutate: deactivate, isPending: isDeactivating } = useMutation({
    mutationFn: (templateId: string) =>
      apiClient
        .put<PostopTemplate>(`/postop/templates/${templateId}`, {
          is_active: false,
        })
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: POSTOP_TEMPLATES_KEY });
      success("Plantilla desactivada", "La plantilla ya no estará disponible.");
      setOpenMenuId(null);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo desactivar la plantilla.";
      toastError("Error", message);
    },
  });

  if (templates.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[hsl(var(--border))] p-12 text-center">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          No hay plantillas post-operatorias. Crea la primera.
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-[hsl(var(--border))] overflow-hidden"
      ref={menuRef}
    >
      {/* Header row */}
      <div className="hidden md:grid grid-cols-[1fr_2fr_auto_auto_auto] gap-4 px-4 py-3 bg-slate-50 dark:bg-zinc-900 border-b border-[hsl(var(--border))] text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
        <span>Procedimiento</span>
        <span>Título</span>
        <span>Canal</span>
        <span>Por defecto</span>
        <span />
      </div>

      {/* Rows */}
      <ul>
        {templates.map((t, idx) => {
          const channelConfig =
            CHANNEL_LABELS[t.channel_preference] ?? CHANNEL_LABELS.all;
          const procedureLabel =
            PROCEDURE_LABELS[t.procedure_type] ?? t.procedure_type;

          return (
            <li
              key={t.id}
              className={`grid grid-cols-1 md:grid-cols-[1fr_2fr_auto_auto_auto] gap-2 md:gap-4 px-4 py-3 items-start md:items-center text-sm ${
                idx < templates.length - 1
                  ? "border-b border-[hsl(var(--border))]"
                  : ""
              } ${!t.is_active ? "opacity-50" : ""}`}
            >
              {/* Procedure type */}
              <span className="font-medium text-[hsl(var(--foreground))]">
                {procedureLabel}
              </span>

              {/* Title */}
              <span className="text-[hsl(var(--muted-foreground))] truncate">
                {t.title}
              </span>

              {/* Channel badge */}
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium w-fit ${channelConfig.color}`}
              >
                {channelConfig.label}
              </span>

              {/* Default indicator */}
              <span className="flex items-center justify-center">
                {t.is_default ? (
                  <Star
                    className="h-4 w-4 text-amber-500 fill-amber-500"
                    aria-label="Plantilla por defecto"
                  />
                ) : (
                  <span className="h-4 w-4 block" />
                )}
              </span>

              {/* Actions menu */}
              <div className="relative flex justify-end">
                <button
                  onClick={() =>
                    setOpenMenuId(openMenuId === t.id ? null : t.id)
                  }
                  aria-label="Acciones"
                  className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors text-[hsl(var(--muted-foreground))]"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>

                {openMenuId === t.id && (
                  <div className="absolute right-0 top-8 z-20 min-w-[160px] rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] shadow-lg py-1">
                    <button
                      onClick={() => {
                        setOpenMenuId(null);
                        onEdit(t);
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-zinc-800 transition-colors"
                    >
                      <Pencil className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                      Editar
                    </button>
                    {t.is_active && (
                      <button
                        onClick={() => deactivate(t.id)}
                        disabled={isDeactivating}
                        className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors disabled:opacity-50"
                      >
                        <PowerOff className="h-3.5 w-3.5" />
                        Desactivar
                      </button>
                    )}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
