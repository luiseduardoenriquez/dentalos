import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, CheckCircle } from "lucide-react";

// Short trust signals rendered beneath the CTAs
const TRUST_BULLETS = [
  "Sin tarjeta de credito",
  "Configuracion en 5 minutos",
  "Soporte en espanol",
];

// CSS-only dashboard mockup — represents a dental clinic management UI
function DashboardMockup() {
  return (
    <div
      className="
        relative w-full max-w-lg mx-auto
        rounded-2xl border-2 border-primary-200 dark:border-primary-800
        bg-white dark:bg-zinc-900
        shadow-2xl shadow-primary-100 dark:shadow-primary-950/40
        overflow-hidden
      "
      aria-hidden="true"
    >
      {/* Mockup title bar */}
      <div className="flex items-center gap-2 px-4 py-3 bg-slate-50 dark:bg-zinc-800 border-b border-[hsl(var(--border))]">
        <span className="w-3 h-3 rounded-full bg-red-400" />
        <span className="w-3 h-3 rounded-full bg-yellow-400" />
        <span className="w-3 h-3 rounded-full bg-green-400" />
        <div className="ml-2 flex-1 h-5 rounded bg-slate-200 dark:bg-zinc-700 max-w-xs" />
      </div>

      <div className="p-4 space-y-3">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Pacientes hoy", value: "12", color: "bg-primary-50 dark:bg-primary-950 border-primary-100 dark:border-primary-900" },
            { label: "Pendientes", value: "4", color: "bg-amber-50 dark:bg-amber-950 border-amber-100 dark:border-amber-900" },
            { label: "Completadas", value: "8", color: "bg-green-50 dark:bg-green-950 border-green-100 dark:border-green-900" },
          ].map((stat) => (
            <div
              key={stat.label}
              className={`rounded-lg border p-2.5 ${stat.color}`}
            >
              <p className="text-xs text-slate-500 dark:text-zinc-400 leading-tight">{stat.label}</p>
              <p className="text-xl font-bold text-slate-800 dark:text-zinc-100 mt-0.5">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Odontogram placeholder */}
        <div className="rounded-lg border border-[hsl(var(--border))] p-3 bg-slate-50 dark:bg-zinc-800">
          <div className="flex items-center justify-between mb-2">
            <div className="h-3 w-24 rounded bg-slate-200 dark:bg-zinc-600" />
            <div className="h-3 w-14 rounded bg-primary-200 dark:bg-primary-800" />
          </div>
          {/* Tooth grid rows */}
          <div className="flex justify-center gap-1 mb-1">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`upper-r-${i}`}
                className={`w-5 h-5 rounded-sm border ${
                  i === 2
                    ? "bg-primary-500 border-primary-600"
                    : i === 5
                    ? "bg-amber-400 border-amber-500"
                    : "bg-white dark:bg-zinc-700 border-slate-300 dark:border-zinc-600"
                }`}
              />
            ))}
            <div className="w-1" />
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`upper-l-${i}`}
                className="w-5 h-5 rounded-sm border bg-white dark:bg-zinc-700 border-slate-300 dark:border-zinc-600"
              />
            ))}
          </div>
          <div className="flex justify-center gap-1">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`lower-r-${i}`}
                className={`w-5 h-5 rounded-sm border ${
                  i === 4
                    ? "bg-green-400 border-green-500"
                    : "bg-white dark:bg-zinc-700 border-slate-300 dark:border-zinc-600"
                }`}
              />
            ))}
            <div className="w-1" />
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`lower-l-${i}`}
                className="w-5 h-5 rounded-sm border bg-white dark:bg-zinc-700 border-slate-300 dark:border-zinc-600"
              />
            ))}
          </div>
        </div>

        {/* Appointment list */}
        <div className="space-y-2">
          {[
            { name: "Maria G.", time: "09:00", tag: "Revision", tagColor: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
            { name: "Carlos R.", time: "10:30", tag: "Endodoncia", tagColor: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300" },
            { name: "Ana L.", time: "12:00", tag: "Limpieza", tagColor: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300" },
          ].map((appt) => (
            <div
              key={appt.name}
              className="flex items-center justify-between rounded-md border border-[hsl(var(--border))] px-3 py-2 bg-white dark:bg-zinc-800"
            >
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                  <span className="text-xs font-semibold text-primary-700 dark:text-primary-300">
                    {appt.name[0]}
                  </span>
                </div>
                <span className="text-xs font-medium text-slate-700 dark:text-zinc-300">{appt.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 dark:text-zinc-500">{appt.time}</span>
                <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${appt.tagColor}`}>
                  {appt.tag}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Flow indicator: Odontogram → Factura */}
        <div className="flex items-center justify-center gap-2 pt-1">
          {["Odontograma", "Plan", "Factura"].map((step, idx) => (
            <div key={step} className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                <div className={`w-2 h-2 rounded-full ${idx === 0 ? "bg-primary-500" : idx === 1 ? "bg-secondary-500" : "bg-green-500"}`} />
                <span className="text-xs text-slate-500 dark:text-zinc-400">{step}</span>
              </div>
              {idx < 2 && (
                <ArrowRight className="w-3 h-3 text-slate-300 dark:text-zinc-600" />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Hero Section ─────────────────────────────────────────────────────────────

export function HeroSection() {
  return (
    <section
      className="
        relative pt-24 pb-16 md:pb-24
        bg-gradient-to-b from-primary-50 to-white
        dark:from-primary-950/30 dark:to-zinc-950
        overflow-hidden
      "
    >
      {/* Decorative background blobs */}
      <div
        className="absolute inset-0 pointer-events-none overflow-hidden"
        aria-hidden="true"
      >
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-primary-100/60 dark:bg-primary-900/20 blur-3xl" />
        <div className="absolute top-1/2 -left-32 w-72 h-72 rounded-full bg-secondary-100/50 dark:bg-secondary-900/20 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">

          {/* Left column — copy */}
          <div className="text-center lg:text-left">
            {/* Category badge */}
            <div className="inline-flex items-center gap-2 rounded-full bg-primary-100 dark:bg-primary-900/50 px-4 py-1.5 mb-6">
              <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
              <span className="text-xs font-semibold text-primary-700 dark:text-primary-300 tracking-wide uppercase">
                Software dental para Colombia
              </span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-zinc-50 leading-[1.1]">
              Tu clinica dental,{" "}
              <span className="text-primary-600 dark:text-primary-400">
                mas rapida que el papel
              </span>
            </h1>

            <p className="mt-6 text-lg sm:text-xl text-slate-600 dark:text-zinc-300 leading-relaxed max-w-2xl mx-auto lg:mx-0">
              Del odontograma a la factura DIAN en un solo flujo. Historia
              clinica digital, agenda inteligente y cumplimiento RIPS desde el
              primer dia. Sin instalaciones, sin complicaciones.
            </p>

            {/* CTA buttons */}
            <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Button size="lg" asChild>
                <Link href="/register">
                  Empieza gratis
                  <ArrowRight className="ml-1 w-4 h-4" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href="/pricing">Ver precios</Link>
              </Button>
            </div>

            {/* Trust bullets */}
            <ul className="mt-6 flex flex-col sm:flex-row gap-x-6 gap-y-2 justify-center lg:justify-start">
              {TRUST_BULLETS.map((bullet) => (
                <li
                  key={bullet}
                  className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-zinc-400"
                >
                  <CheckCircle className="w-4 h-4 shrink-0 text-green-500" />
                  {bullet}
                </li>
              ))}
            </ul>
          </div>

          {/* Right column — dashboard mockup */}
          <div className="flex justify-center lg:justify-end">
            <DashboardMockup />
          </div>
        </div>
      </div>
    </section>
  );
}
