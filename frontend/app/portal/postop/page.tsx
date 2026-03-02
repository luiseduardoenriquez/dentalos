"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { ClipboardList, ChevronDown, AlertCircle } from "lucide-react";
import { portalApiGet } from "@/lib/portal-api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PostopInstruction {
  id: string;
  procedure_type: string;
  procedure_label: string | null;
  title: string;
  instruction_content: string;
  sent_at: string;
  channel: "whatsapp" | "email" | "portal" | "all";
  appointment_date: string | null;
  doctor_name: string | null;
}

interface PostopInstructionsResponse {
  items: PostopInstruction[];
  total: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const PROCEDURE_LABELS: Record<string, string> = {
  resina: "Resina / Composite",
  endodoncia: "Endodoncia",
  exodoncia: "Exodoncia",
  profilaxis: "Profilaxis / Limpieza",
  implante: "Implante",
  cirugia_periodontal: "Cirugía periodontal",
  corona: "Corona / Prótesis",
  ortodoncia: "Ortodoncia",
  blanqueamiento: "Blanqueamiento",
  sedacion: "Sedación",
  otro: "Procedimiento dental",
};

const CHANNEL_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  email: "Correo",
  portal: "Portal",
  all: "Todos los canales",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-CO", {
    weekday: "short",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function InstructionsSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-[hsl(var(--border))] p-4 space-y-2"
        >
          <div className="h-5 w-48 rounded bg-slate-200 dark:bg-zinc-700" />
          <div className="h-4 w-32 rounded bg-slate-100 dark:bg-zinc-800" />
        </div>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * /portal/postop
 *
 * Patient portal post-operative instructions page.
 * Lists all post-op instructions the patient has received.
 * Each entry is expandable to read the full content.
 */
export default function PortalPostopPage() {
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["portal", "postop"],
    queryFn: () =>
      portalApiGet<PostopInstructionsResponse>("/portal/postop"),
    staleTime: 5 * 60_000,
  });

  const instructions = data?.items ?? [];

  // ─── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6 max-w-2xl mx-auto">
        <div className="h-8 w-64 rounded bg-slate-200 dark:bg-zinc-700 animate-pulse" />
        <InstructionsSkeleton />
      </div>
    );
  }

  // ─── Error ──────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="max-w-2xl mx-auto flex flex-col items-center justify-center py-16 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          Error al cargar las instrucciones
        </p>
        <button
          onClick={() => refetch()}
          className="text-sm text-teal-600 hover:underline"
        >
          Reintentar
        </button>
      </div>
    );
  }

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))] flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-teal-600" />
          Cuidados post-operatorios
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Instrucciones de cuidado que recibiste después de tus procedimientos.
        </p>
      </div>

      {/* Empty state */}
      {instructions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[hsl(var(--border))] py-14 text-center">
          <ClipboardList className="h-8 w-8 text-[hsl(var(--muted-foreground))] mx-auto mb-3" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Aún no tienes instrucciones post-operatorias.
          </p>
          <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
            Tu clínica las enviará después de tus procedimientos.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {instructions.map((instr) => {
            const isExpanded = expandedId === instr.id;
            const procedureLabel =
              instr.procedure_label ??
              PROCEDURE_LABELS[instr.procedure_type] ??
              instr.procedure_type;

            return (
              <li
                key={instr.id}
                className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden"
              >
                {/* Summary row — tap to expand */}
                <button
                  onClick={() =>
                    setExpandedId(isExpanded ? null : instr.id)
                  }
                  aria-expanded={isExpanded}
                  className="w-full text-left px-4 py-4 flex items-start justify-between gap-3 hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    {/* Procedure type badge */}
                    <span className="inline-flex items-center px-2 py-0.5 mb-1.5 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-950/30 dark:text-teal-300 text-xs font-medium">
                      {procedureLabel}
                    </span>

                    <p className="text-sm font-medium text-[hsl(var(--foreground))] leading-snug">
                      {instr.title}
                    </p>

                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-[hsl(var(--muted-foreground))]">
                      <span>{formatDate(instr.sent_at)}</span>
                      {instr.doctor_name && (
                        <>
                          <span aria-hidden="true">·</span>
                          <span>Dr. {instr.doctor_name}</span>
                        </>
                      )}
                      <span aria-hidden="true">·</span>
                      <span>
                        Enviado por {CHANNEL_LABELS[instr.channel] ?? instr.channel}
                      </span>
                    </div>
                  </div>

                  <ChevronDown
                    className={`h-4 w-4 flex-shrink-0 text-[hsl(var(--muted-foreground))] mt-1 transition-transform duration-150 ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="border-t border-[hsl(var(--border))] px-4 py-4 bg-slate-50 dark:bg-zinc-900/50">
                    {instr.appointment_date && (
                      <p className="mb-3 text-xs text-[hsl(var(--muted-foreground))]">
                        Cita:{" "}
                        {new Date(instr.appointment_date).toLocaleDateString(
                          "es-CO",
                          {
                            day: "numeric",
                            month: "long",
                            year: "numeric",
                          },
                        )}
                      </p>
                    )}

                    {/* Content — render as preformatted text to preserve line breaks */}
                    <div className="text-sm text-[hsl(var(--foreground))] leading-relaxed whitespace-pre-wrap">
                      {instr.instruction_content}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
