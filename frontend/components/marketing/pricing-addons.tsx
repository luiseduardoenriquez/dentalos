import { Check, Mic, ScanLine } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Addon {
  id: string;
  icon: React.ElementType;
  name: string;
  price: number;
  unit: string;
  tagline: string;
  features: string[];
  badgeLabel: string;
}

// ─── Add-on Data ───────────────────────────────────────────────────────────────

const ADDONS: Addon[] = [
  {
    id: "ai-voz",
    icon: Mic,
    name: "AI Voz",
    price: 10,
    unit: "/doctor/mes",
    tagline: "Dictado por voz para historia clinica",
    features: [
      "Transcripcion automatica en tiempo real",
      "Compatible con odontograma y evolucion",
      "Optimizado para espanol colombiano",
      "Corrector de terminologia odontologica",
      "Historial de dictados auditables",
    ],
    badgeLabel: "Add-on",
  },
  {
    id: "ai-radiografia",
    icon: ScanLine,
    name: "AI Radiografia",
    price: 20,
    unit: "/doctor/mes",
    tagline: "Analisis de radiografias con inteligencia artificial",
    features: [
      "Deteccion automatica de caries y lesiones",
      "Sugerencias de diagnostico con IA",
      "Compatible con formato DICOM",
      "Informe generado en segundos",
      "Revision por el profesional siempre requerida",
    ],
    badgeLabel: "Add-on",
  },
];

// ─── Addon Card ────────────────────────────────────────────────────────────────

function AddonCard({ addon }: { addon: Addon }) {
  const Icon = addon.icon;

  return (
    <Card className="relative flex flex-col hover:shadow-md transition-shadow duration-200 border-secondary-200/60 dark:border-secondary-800/40">
      {/* Accent top bar */}
      <div
        className="absolute inset-x-0 top-0 h-1 rounded-t-lg bg-secondary-600"
        aria-hidden="true"
      />

      <CardHeader className="pt-7">
        <div className="flex items-start justify-between gap-4">
          {/* Icon */}
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-secondary-50 dark:bg-secondary-900/30 border border-secondary-200/60 dark:border-secondary-700/40 shrink-0">
            <Icon
              className="h-6 w-6 text-secondary-600 dark:text-secondary-400"
              aria-hidden="true"
            />
          </div>
          <Badge variant="secondary" className="mt-1 shrink-0">
            {addon.badgeLabel}
          </Badge>
        </div>

        <div className="mt-4">
          <CardTitle className="text-xl font-bold text-slate-900 dark:text-zinc-100">
            {addon.name}
          </CardTitle>

          {/* Price */}
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-slate-900 dark:text-zinc-100">
              ${addon.price}
            </span>
            <span className="text-sm text-slate-500 dark:text-zinc-500">
              {addon.unit}
            </span>
          </div>

          <CardDescription className="mt-2 text-sm leading-relaxed">
            {addon.tagline}
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="flex-1">
        <ul className="space-y-2.5" aria-label={`Funciones de ${addon.name}`}>
          {addon.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2.5">
              <Check
                className="mt-0.5 h-4 w-4 shrink-0 text-secondary-600 dark:text-secondary-400"
                aria-hidden="true"
              />
              <span className="text-sm text-slate-700 dark:text-zinc-300">
                {feature}
              </span>
            </li>
          ))}
        </ul>

        <p className="mt-5 text-xs text-slate-500 dark:text-zinc-500">
          Disponible a partir del plan Starter. Se agrega por doctor activo.
        </p>
      </CardContent>
    </Card>
  );
}

// ─── Main Export ───────────────────────────────────────────────────────────────

export function PricingAddons() {
  return (
    <section
      className="py-16 px-4 sm:px-6 lg:px-8 bg-white dark:bg-zinc-950"
      aria-labelledby="addons-heading"
    >
      <div className="mx-auto max-w-5xl">
        {/* Section header */}
        <div className="text-center mb-10">
          <Badge variant="secondary" className="mb-4 text-xs tracking-wider uppercase">
            Inteligencia Artificial
          </Badge>
          <h2
            id="addons-heading"
            className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-zinc-50"
          >
            Complementos con IA
          </h2>
          <p className="mt-3 text-slate-600 dark:text-zinc-400 max-w-xl mx-auto">
            Potencia tu flujo de trabajo con herramientas de inteligencia artificial
            disenadas especificamente para la practica odontologica.
          </p>
        </div>

        {/* Add-on cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {ADDONS.map((addon) => (
            <AddonCard key={addon.id} addon={addon} />
          ))}
        </div>

        {/* Disclaimer */}
        <p className="mt-8 text-center text-xs text-slate-400 dark:text-zinc-600 max-w-lg mx-auto">
          Los complementos de IA son herramientas de apoyo clinico. El diagnostico
          y decision final siempre corresponde al profesional de la salud.
        </p>
      </div>
    </section>
  );
}
