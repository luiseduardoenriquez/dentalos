import { Quote } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface Testimonial {
  quote: string;
  name: string;
  role: string;
  clinic: string;
  city: string;
  /** Initials for the avatar circle */
  initials: string;
  /** Tailwind background color class for the avatar */
  avatarBg: string;
  avatarText: string;
  /** Star rating out of 5 */
  rating: 5;
}

const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      "Antes tardaba 40 minutos llenando papeles por paciente. Con DentalOS lo hago en 8 minutos y la factura queda lista automaticamente. No me imagino volver atras.",
    name: "Dra. Maria Fernanda Lopez",
    role: "Odontologa General",
    clinic: "Clinica Dental Sonrisa",
    city: "Bogota, Colombia",
    initials: "ML",
    avatarBg: "bg-primary-100 dark:bg-primary-900",
    avatarText: "text-primary-700 dark:text-primary-300",
    rating: 5,
  },
  {
    quote:
      "El odontograma digital es increible. Puedo ver el historial completo del paciente, sus radiografias y el plan de tratamiento en una sola pantalla. El dictado por voz me ahorra 30 minutos al dia.",
    name: "Dr. Carlos Andres Ramirez",
    role: "Especialista en Endodoncia",
    clinic: "OdontoSalud",
    city: "Medellin, Colombia",
    initials: "CR",
    avatarBg: "bg-secondary-100 dark:bg-secondary-900",
    avatarText: "text-secondary-700 dark:text-secondary-300",
    rating: 5,
  },
  {
    quote:
      "Los reportes RIPS y la facturacion DIAN me quitaron un peso enorme. Antes contrataba un contador solo para eso. Ahora lo hace DentalOS en segundos y sin errores.",
    name: "Dra. Valentina Torres",
    role: "Directora Clinica",
    clinic: "Dental Center",
    city: "Cali, Colombia",
    initials: "VT",
    avatarBg: "bg-accent-100 dark:bg-accent-900",
    avatarText: "text-accent-700 dark:text-accent-300",
    rating: 5,
  },
];

// Renders five filled star SVG icons
function StarRating() {
  return (
    <div className="flex gap-0.5" aria-label="5 estrellas de 5">
      {Array.from({ length: 5 }).map((_, i) => (
        <svg
          key={i}
          className="w-4 h-4 text-amber-400"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

// ─── Testimonials Section ─────────────────────────────────────────────────────

export function TestimonialsSection() {
  return (
    <section className="py-16 md:py-24 bg-white dark:bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

        {/* Section header */}
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-zinc-50">
            Lo que dicen los dentistas
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-500 dark:text-zinc-400">
            Clinicas en toda Colombia ya estan ahorrando tiempo y cumpliendo con
            la regulacion gracias a DentalOS.
          </p>
        </div>

        {/* Testimonials grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {TESTIMONIALS.map((t) => (
            <TestimonialCard key={t.name} testimonial={t} />
          ))}
        </div>

        {/* Social proof bar */}
        <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-8 text-center">
          {[
            { value: "200+", label: "Clinicas activas" },
            { value: "4.9/5", label: "Calificacion promedio" },
            { value: "98%", label: "Tasa de retencion" },
          ].map((stat) => (
            <div key={stat.label} className="flex flex-col gap-0.5">
              <span className="text-3xl font-extrabold text-primary-600 dark:text-primary-400">
                {stat.value}
              </span>
              <span className="text-sm text-slate-500 dark:text-zinc-400">
                {stat.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Testimonial Card ─────────────────────────────────────────────────────────

function TestimonialCard({ testimonial: t }: { testimonial: Testimonial }) {
  return (
    <Card className="flex flex-col justify-between h-full hover:shadow-md transition-shadow duration-200">
      <CardContent className="pt-6 flex flex-col gap-4 flex-1">

        {/* Stars */}
        <StarRating />

        {/* Quote icon + text */}
        <div className="relative">
          <Quote
            className="absolute -top-1 -left-1 w-6 h-6 text-primary-200 dark:text-primary-800 shrink-0"
            aria-hidden="true"
          />
          <blockquote className="pl-6 text-sm text-slate-600 dark:text-zinc-300 leading-relaxed">
            &ldquo;{t.quote}&rdquo;
          </blockquote>
        </div>

        {/* Spacer pushes author to bottom */}
        <div className="flex-1" />

        {/* Author */}
        <div className="flex items-center gap-3 pt-2 border-t border-[hsl(var(--border))]">
          {/* Avatar */}
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 font-semibold text-sm ${t.avatarBg} ${t.avatarText}`}
            aria-hidden="true"
          >
            {t.initials}
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-zinc-50 leading-tight">
              {t.name}
            </p>
            <p className="text-xs text-slate-500 dark:text-zinc-400 leading-tight">
              {t.role} &middot; {t.clinic}
            </p>
            <p className="text-xs text-slate-400 dark:text-zinc-500 leading-tight">
              {t.city}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
