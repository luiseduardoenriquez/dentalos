"use client";

import { usePortalOdontogram } from "@/lib/hooks/use-portal";

// ─── Constants ────────────────────────────────────────────────────────────────

const CONDITION_COLORS: Record<string, { bg: string; dot: string; label: string }> = {
  caries: {
    bg: "bg-red-100 dark:bg-red-950/30",
    dot: "bg-red-500",
    label: "Caries",
  },
  restoration: {
    bg: "bg-blue-100 dark:bg-blue-950/30",
    dot: "bg-blue-500",
    label: "Restauración",
  },
  crown: {
    bg: "bg-yellow-100 dark:bg-yellow-950/30",
    dot: "bg-yellow-500",
    label: "Corona",
  },
  extraction: {
    bg: "bg-slate-100 dark:bg-zinc-800",
    dot: "bg-slate-500",
    label: "Extracción",
  },
  endodontics: {
    bg: "bg-purple-100 dark:bg-purple-950/30",
    dot: "bg-purple-500",
    label: "Endodoncia",
  },
  implant: {
    bg: "bg-green-100 dark:bg-green-950/30",
    dot: "bg-green-500",
    label: "Implante",
  },
  fracture: {
    bg: "bg-orange-100 dark:bg-orange-950/30",
    dot: "bg-orange-500",
    label: "Fractura",
  },
};

// Upper and lower arch tooth numbers in FDI notation
const UPPER_RIGHT = ["18", "17", "16", "15", "14", "13", "12", "11"];
const UPPER_LEFT = ["21", "22", "23", "24", "25", "26", "27", "28"];
const LOWER_RIGHT = ["48", "47", "46", "45", "44", "43", "42", "41"];
const LOWER_LEFT = ["31", "32", "33", "34", "35", "36", "37", "38"];

// ─── Tooth Cell ───────────────────────────────────────────────────────────────

function ToothCell({
  toothNumber,
  conditions,
}: {
  toothNumber: string;
  conditions: {
    condition_code: string;
    condition_name: string;
    surface: string | null;
    description: string | null;
  }[];
}) {
  const primaryCondition = conditions[0];
  const colorConfig = primaryCondition
    ? CONDITION_COLORS[primaryCondition.condition_code]
    : null;

  return (
    <div className="relative group flex flex-col items-center gap-0.5">
      <div
        className={`w-9 h-9 md:w-10 md:h-10 rounded-lg border-2 flex items-center justify-center text-xs font-mono font-medium transition-colors ${
          conditions.length > 0
            ? `${colorConfig?.bg ?? "bg-slate-100 dark:bg-zinc-800"} border-transparent`
            : "bg-white dark:bg-zinc-900 border-[hsl(var(--border))] hover:border-primary-300"
        }`}
      >
        {toothNumber}
      </div>

      {/* Condition indicator dots */}
      {conditions.length > 0 && (
        <div className="flex gap-0.5">
          {conditions.slice(0, 3).map((cond, i) => (
            <div
              key={i}
              className={`w-1.5 h-1.5 rounded-full ${
                CONDITION_COLORS[cond.condition_code]?.dot ?? "bg-slate-400"
              }`}
            />
          ))}
        </div>
      )}

      {/* Tooltip on hover */}
      {conditions.length > 0 && (
        <div className="hidden group-hover:block absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 p-2.5 bg-zinc-900 dark:bg-zinc-700 text-white rounded-xl text-xs shadow-xl">
          <p className="font-semibold mb-1.5">Diente {toothNumber}</p>
          <div className="space-y-1">
            {conditions.map((cond, i) => (
              <div key={i} className="flex items-start gap-1.5">
                <div
                  className={`w-2 h-2 rounded-full mt-0.5 shrink-0 ${
                    CONDITION_COLORS[cond.condition_code]?.dot ?? "bg-slate-400"
                  }`}
                />
                <div>
                  <span>{cond.condition_name}</span>
                  {cond.surface && (
                    <span className="text-zinc-400 ml-1">
                      (cara {cond.surface})
                    </span>
                  )}
                  {cond.description && (
                    <p className="text-zinc-400 text-xs mt-0.5">
                      {cond.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Arch Row ─────────────────────────────────────────────────────────────────

function ArchRow({
  toothNumbers,
  teethMap,
  label,
}: {
  toothNumbers: string[];
  teethMap: Map<
    string,
    {
      condition_code: string;
      condition_name: string;
      surface: string | null;
      description: string | null;
    }[]
  >;
  label: string;
}) {
  return (
    <div>
      <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1 font-medium">
        {label}
      </p>
      <div className="flex gap-1 flex-wrap">
        {toothNumbers.map((num) => (
          <ToothCell
            key={num}
            toothNumber={num}
            conditions={teethMap.get(num) ?? []}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalOdontogram() {
  const { data: odontogram, isLoading, isError, error, refetch } = usePortalOdontogram();

  // Build a map from tooth_number → conditions for fast lookup
  const teethMap = new Map<
    string,
    {
      condition_code: string;
      condition_name: string;
      surface: string | null;
      description: string | null;
    }[]
  >();

  if (odontogram) {
    for (const tooth of odontogram.teeth) {
      if (tooth.conditions.length > 0) {
        teethMap.set(tooth.tooth_number, tooth.conditions);
      }
    }
  }

  // Count teeth with conditions
  const affectedCount = odontogram?.teeth.filter(
    (t) => t.conditions.length > 0,
  ).length ?? 0;

  const legendEntries = odontogram
    ? Object.entries(odontogram.legend)
    : [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
          Mi odontograma
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Vista de solo lectura de tu estado dental actual
        </p>
      </div>

      {isLoading ? (
        <div className="h-72 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">
            Error al cargar los datos
          </p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      ) : !odontogram || odontogram.teeth.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))]">
          <svg
            className="mx-auto w-12 h-12 text-slate-300 dark:text-zinc-600 mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-[hsl(var(--muted-foreground))]">
            No hay registro de odontograma aún
          </p>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
            Tu odontólogo(a) lo actualizará en tu próxima consulta
          </p>
        </div>
      ) : (
        <>
          {/* Summary chip */}
          {affectedCount > 0 && (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary-50 dark:bg-primary-950/30 text-primary-700 dark:text-primary-400 text-sm">
                <span className="font-semibold">{affectedCount}</span>
                {affectedCount === 1
                  ? "diente con hallazgos"
                  : "dientes con hallazgos"}
              </span>
            </div>
          )}

          {/* Legend */}
          {legendEntries.length > 0 && (
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4">
              <h2 className="text-sm font-semibold text-[hsl(var(--foreground))] mb-3">
                Leyenda de condiciones
              </h2>
              <div className="flex flex-wrap gap-x-4 gap-y-2">
                {legendEntries.map(([code, name]) => {
                  const cfg = CONDITION_COLORS[code];
                  return (
                    <div key={code} className="flex items-center gap-1.5">
                      <div
                        className={`w-3 h-3 rounded-full ${cfg?.dot ?? "bg-slate-400"}`}
                      />
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        {name}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Odontogram — FDI layout */}
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4 space-y-5">
            {/* Upper arch */}
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-wide text-[hsl(var(--muted-foreground))] font-semibold">
                Maxilar superior
              </p>
              <div className="flex gap-4 flex-wrap">
                <ArchRow
                  toothNumbers={UPPER_RIGHT}
                  teethMap={teethMap}
                  label="Derecha"
                />
                <ArchRow
                  toothNumbers={UPPER_LEFT}
                  teethMap={teethMap}
                  label="Izquierda"
                />
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-dashed border-[hsl(var(--border))]" />

            {/* Lower arch */}
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-wide text-[hsl(var(--muted-foreground))] font-semibold">
                Maxilar inferior
              </p>
              <div className="flex gap-4 flex-wrap">
                <ArchRow
                  toothNumbers={LOWER_RIGHT}
                  teethMap={teethMap}
                  label="Derecha"
                />
                <ArchRow
                  toothNumbers={LOWER_LEFT}
                  teethMap={teethMap}
                  label="Izquierda"
                />
              </div>
            </div>
          </div>

          {/* Conditions list — accessible text fallback */}
          {affectedCount > 0 && (
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4">
              <h2 className="text-sm font-semibold text-[hsl(var(--foreground))] mb-3">
                Detalle de hallazgos
              </h2>
              <div className="space-y-3">
                {odontogram.teeth
                  .filter((t) => t.conditions.length > 0)
                  .map((tooth) => (
                    <div
                      key={tooth.tooth_number}
                      className="flex items-start gap-3"
                    >
                      <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-zinc-800 flex items-center justify-center text-xs font-mono font-medium shrink-0">
                        {tooth.tooth_number}
                      </div>
                      <div className="flex-1 min-w-0">
                        {tooth.conditions.map((cond, i) => {
                          const cfg = CONDITION_COLORS[cond.condition_code];
                          return (
                            <div
                              key={i}
                              className="flex items-center gap-2 text-sm"
                            >
                              <div
                                className={`w-2 h-2 rounded-full shrink-0 ${cfg?.dot ?? "bg-slate-400"}`}
                              />
                              <span className="text-[hsl(var(--foreground))]">
                                {cond.condition_name}
                              </span>
                              {cond.surface && (
                                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                                  cara {cond.surface}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Last updated */}
          {odontogram.last_updated && (
            <p className="text-xs text-[hsl(var(--muted-foreground))] text-center">
              Última actualización:{" "}
              {new Date(odontogram.last_updated).toLocaleDateString("es-CO", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          )}
        </>
      )}
    </div>
  );
}
