import { AlertTriangle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

// Each item contrasts the old pain point with the DentalOS solution
interface ProblemItem {
  painTitle: string;
  painBody: string;
  solutionTitle: string;
  solutionBody: string;
}

const PROBLEMS: ProblemItem[] = [
  {
    painTitle: "Triple digitacion",
    painBody:
      "Cada procedimiento se anota a mano, luego en el sistema y otra vez en la factura. Horas perdidas en papel que podrian estar con pacientes.",
    solutionTitle: "Flujo automatico del odontograma a la factura",
    solutionBody:
      "Registra el procedimiento una vez en el odontograma. DentalOS genera el plan de tratamiento, la cotizacion y la factura DIAN automaticamente.",
  },
  {
    painTitle: "Software de los 90s",
    painBody:
      "Interfaces lentas, instalacion en un solo PC, sin acceso remoto y actualizaciones que tardan semanas. Tu equipo odia el software.",
    solutionTitle: "Interfaz moderna, rapida y en la nube",
    solutionBody:
      "Disenado para ser mas rapido que el papel. Accede desde cualquier dispositivo, en cualquier lugar, con actualizaciones automaticas y sin instalacion.",
  },
  {
    painTitle: "Sin cumplimiento DIAN ni RIPS",
    painBody:
      "La facturacion electronica obligatoria y los reportes RIPS te quitan el sueno. Multas, rechazos y horas perdidas en tramites.",
    solutionTitle: "DIAN y RIPS integrados desde el dia 1",
    solutionBody:
      "Factura electronica certificada ante la DIAN y reportes RIPS en un clic. Cumple la Resolucion 1888 sin esfuerzo adicional.",
  },
];

// ─── Problem Section ──────────────────────────────────────────────────────────

export function ProblemSection() {
  return (
    <section className="py-16 md:py-24 bg-white dark:bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

        {/* Section header */}
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-zinc-50">
            El software dental{" "}
            <span className="text-primary-600 dark:text-primary-400">
              que Colombia necesitaba
            </span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-500 dark:text-zinc-400">
            Conocemos los problemas reales de las clinicas. DentalOS los
            resuelve uno a uno.
          </p>
        </div>

        {/* Problems grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {PROBLEMS.map((item) => (
            <ProblemCard key={item.painTitle} item={item} />
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Problem Card ─────────────────────────────────────────────────────────────

function ProblemCard({ item }: { item: ProblemItem }) {
  return (
    <div className="flex flex-col gap-0 rounded-xl overflow-hidden border border-[hsl(var(--border))] shadow-sm">

      {/* Pain block — muted, slate tones */}
      <div className="flex-1 p-6 bg-slate-50 dark:bg-zinc-800">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "shrink-0 flex items-center justify-center w-9 h-9 rounded-lg",
              "bg-slate-200 dark:bg-zinc-700",
            )}
          >
            <AlertTriangle
              className="w-5 h-5 text-slate-500 dark:text-zinc-400"
              aria-hidden="true"
            />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-zinc-500 mb-1">
              El problema
            </p>
            <h3 className="font-semibold text-slate-700 dark:text-zinc-200 text-base leading-snug">
              {item.painTitle}
            </h3>
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-500 dark:text-zinc-400 leading-relaxed">
          {item.painBody}
        </p>
      </div>

      {/* Divider with arrow */}
      <div
        className="flex items-center justify-center py-1.5 bg-primary-600 dark:bg-primary-700"
        aria-hidden="true"
      >
        <svg
          className="w-4 h-4 text-white"
          fill="none"
          viewBox="0 0 16 16"
          aria-hidden="true"
        >
          <path
            d="M8 2v12M8 14l-4-4M8 14l4-4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* Solution block — primary/green tones */}
      <div className="flex-1 p-6 bg-primary-50 dark:bg-primary-950/40">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "shrink-0 flex items-center justify-center w-9 h-9 rounded-lg",
              "bg-primary-100 dark:bg-primary-900",
            )}
          >
            <CheckCircle
              className="w-5 h-5 text-primary-600 dark:text-primary-400"
              aria-hidden="true"
            />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-primary-500 dark:text-primary-400 mb-1">
              La solucion
            </p>
            <h3 className="font-semibold text-primary-800 dark:text-primary-200 text-base leading-snug">
              {item.solutionTitle}
            </h3>
          </div>
        </div>
        <p className="mt-4 text-sm text-primary-700 dark:text-primary-300 leading-relaxed">
          {item.solutionBody}
        </p>
      </div>
    </div>
  );
}
