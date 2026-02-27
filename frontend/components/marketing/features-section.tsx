import {
  FileText,
  Calendar,
  Receipt,
  UserCircle,
  Mic,
  type LucideIcon,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Tooth is not in lucide-react; use a custom SVG fallback component
// that matches the lucide icon contract (w-5 h-5 strokeWidth etc.)
function ToothIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {/* Simplified tooth outline */}
      <path d="M12 2C9 2 6 4 6 7c0 1.5.5 3 1 4.5L8 20c.5 2 2 2 2 2h4s1.5 0 2-2l1-8.5c.5-1.5 1-3 1-4.5 0-3-3-5-6-5z" />
      <path d="M9 7c1-1 5-1 6 0" />
    </svg>
  );
}

interface Feature {
  /** Lucide icon component OR null to use ToothIcon */
  Icon: LucideIcon | null;
  /** Hex background color for the icon circle, expressed as Tailwind classes */
  iconBg: string;
  iconColor: string;
  title: string;
  description: string;
}

const FEATURES: Feature[] = [
  {
    Icon: null, // uses ToothIcon custom SVG
    iconBg: "bg-primary-100 dark:bg-primary-900/50",
    iconColor: "text-primary-600 dark:text-primary-400",
    title: "Odontograma digital",
    description:
      "Registro clinico interactivo por diente. Marca tratamientos, diagnosticos y estados con un clic. Cumple la norma colombiana.",
  },
  {
    Icon: FileText,
    iconBg: "bg-secondary-100 dark:bg-secondary-900/50",
    iconColor: "text-secondary-600 dark:text-secondary-400",
    title: "Historia clinica",
    description:
      "Evolucion clinica, notas de procedimientos y adjuntos radiograficos en un solo lugar. Con firma digital integrada.",
  },
  {
    Icon: Calendar,
    iconBg: "bg-accent-100 dark:bg-accent-900/50",
    iconColor: "text-accent-600 dark:text-accent-400",
    title: "Agenda inteligente",
    description:
      "Programa citas en 3 toques. Recordatorios automaticos por WhatsApp y SMS. Vista diaria, semanal y por doctor.",
  },
  {
    Icon: Receipt,
    iconBg: "bg-green-100 dark:bg-green-900/50",
    iconColor: "text-green-600 dark:text-green-400",
    title: "Facturacion DIAN",
    description:
      "Factura electronica certificada y validada ante la DIAN. Reportes RIPS con un clic. Cumplimiento de Resolucion 1888.",
  },
  {
    Icon: UserCircle,
    iconBg: "bg-purple-100 dark:bg-purple-900/50",
    iconColor: "text-purple-600 dark:text-purple-400",
    title: "Portal del paciente",
    description:
      "Tus pacientes ven su historia, firman consentimientos y descargan facturas desde el celular. Sin llamadas innecesarias.",
  },
  {
    Icon: Mic,
    iconBg: "bg-rose-100 dark:bg-rose-900/50",
    iconColor: "text-rose-600 dark:text-rose-400",
    title: "Dictado por voz",
    description:
      "Dicta el procedimiento y DentalOS lo convierte en el registro clinico completo. Powered by IA. Disponible como complemento.",
  },
];

// ─── Features Section ─────────────────────────────────────────────────────────

export function FeaturesSection() {
  return (
    <section
      id="funciones"
      className="py-16 md:py-24 bg-slate-50 dark:bg-zinc-900/50 scroll-mt-16"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

        {/* Section header */}
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-zinc-50">
            Todo lo que tu clinica necesita
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-500 dark:text-zinc-400">
            Cada herramienta esta disenada para clinicas colombianas, con
            cumplimiento regulatorio incluido desde el primer dia.
          </p>
        </div>

        {/* Features grid — 2 columns on md, 3 on lg */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} feature={feature} />
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Feature Card ─────────────────────────────────────────────────────────────

function FeatureCard({ feature }: { feature: Feature }) {
  const { Icon, iconBg, iconColor, title, description } = feature;

  return (
    <Card className="group hover:shadow-md transition-shadow duration-200">
      <CardHeader>
        {/* Icon circle */}
        <div
          className={cn(
            "flex items-center justify-center w-11 h-11 rounded-xl mb-3",
            iconBg,
          )}
        >
          {Icon ? (
            <Icon className={cn("w-5 h-5", iconColor)} aria-hidden="true" />
          ) : (
            <ToothIcon className={cn("w-5 h-5", iconColor)} />
          )}
        </div>

        <CardTitle className="text-base font-semibold text-slate-900 dark:text-zinc-50 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors duration-150">
          {title}
        </CardTitle>

        <CardDescription className="text-sm leading-relaxed">
          {description}
        </CardDescription>
      </CardHeader>
    </Card>
  );
}
