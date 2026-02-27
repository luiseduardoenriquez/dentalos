import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, ShieldCheck } from "lucide-react";

// ─── CTA Section ──────────────────────────────────────────────────────────────

export function CtaSection() {
  return (
    <section className="py-16 md:py-24 bg-gradient-to-r from-primary-600 to-primary-700 dark:from-primary-700 dark:to-primary-800 relative overflow-hidden">
      {/* Subtle decorative shapes */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white/5 blur-2xl" />
        <div className="absolute -bottom-16 -left-16 w-72 h-72 rounded-full bg-white/5 blur-2xl" />
        {/* Faint grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, transparent, transparent 48px, rgba(255,255,255,1) 48px, rgba(255,255,255,1) 49px), repeating-linear-gradient(90deg, transparent, transparent 48px, rgba(255,255,255,1) 48px, rgba(255,255,255,1) 49px)",
          }}
        />
      </div>

      <div className="relative mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">

        {/* Headline */}
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
          Empieza a usar DentalOS hoy
        </h2>

        {/* Subtext */}
        <p className="mt-4 text-lg sm:text-xl text-primary-100 max-w-2xl mx-auto">
          Plan gratuito para siempre. Sin tarjeta de credito. Sin contratos.
          Solo un software que hace que tu clinica vuele.
        </p>

        {/* CTA button — white background with primary text */}
        <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            size="lg"
            className="
              bg-white text-primary-700 font-semibold
              hover:bg-primary-50
              dark:bg-white dark:text-primary-700 dark:hover:bg-primary-50
              shadow-lg shadow-primary-900/30
              transition-colors duration-150
            "
            asChild
          >
            <Link href="/register">
              Crear cuenta gratis
              <ArrowRight className="ml-1 w-4 h-4" />
            </Link>
          </Button>

          <Button
            size="lg"
            variant="outline"
            className="
              border-white/50 text-white bg-transparent
              hover:bg-white/10 hover:text-white
              dark:border-white/50 dark:text-white dark:hover:bg-white/10
              transition-colors duration-150
            "
            asChild
          >
            <Link href="/pricing">Ver planes</Link>
          </Button>
        </div>

        {/* Trust line */}
        <div className="mt-8 flex items-center justify-center gap-2 text-primary-100">
          <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
          <p className="text-sm">
            Tus datos estan seguros. Cumplimos con la Ley 1581 de proteccion de
            datos de Colombia.
          </p>
        </div>
      </div>
    </section>
  );
}
