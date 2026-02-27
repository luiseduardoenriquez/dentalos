import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ShieldCheck, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PricingCards } from "@/components/marketing/pricing-cards";
import { PricingTable } from "@/components/marketing/pricing-table";
import { PricingAddons } from "@/components/marketing/pricing-addons";
import { FaqSection } from "@/components/marketing/faq-section";

// ─── Metadata ──────────────────────────────────────────────────────────────────

export const metadata: Metadata = {
  title: "Precios — Planes para cada clinica",
  description:
    "DentalOS ofrece planes desde $0 hasta Enterprise. Starter desde $19/doctor/mes, Pro desde $39/doctor/mes con RIPS y DIAN. Todos los planes incluyen 14 dias gratis.",
  keywords: [
    "precios software dental Colombia",
    "plan odontologia Colombia",
    "facturacion DIAN dental",
    "RIPS automatico clinica",
    "software dental gratis",
  ],
  openGraph: {
    title: "Precios — DentalOS | Software Dental Colombia",
    description:
      "Planes desde $0. Starter $19/doctor/mes, Pro $39 con RIPS y DIAN, Clinica $69/sede. Sin contratos ni permanencia.",
    locale: "es_CO",
    type: "website",
  },
  alternates: {
    canonical: "/pricing",
  },
};

// ─── Inline CTA (pricing-specific) ────────────────────────────────────────────

function PricingCta() {
  return (
    <section
      className="py-16 md:py-24 bg-gradient-to-r from-primary-600 to-primary-700 dark:from-primary-700 dark:to-primary-800 relative overflow-hidden"
      aria-labelledby="pricing-cta-heading"
    >
      {/* Decorative background shapes */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white/5 blur-2xl" />
        <div className="absolute -bottom-16 -left-16 w-72 h-72 rounded-full bg-white/5 blur-2xl" />
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, transparent, transparent 48px, rgba(255,255,255,1) 48px, rgba(255,255,255,1) 49px), repeating-linear-gradient(90deg, transparent, transparent 48px, rgba(255,255,255,1) 48px, rgba(255,255,255,1) 49px)",
          }}
        />
      </div>

      <div className="relative mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
        <h2
          id="pricing-cta-heading"
          className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight"
        >
          Listo para modernizar tu clinica?
        </h2>

        <p className="mt-4 text-lg sm:text-xl text-primary-100 max-w-2xl mx-auto">
          Empieza gratis hoy. Sin tarjeta de credito, sin contratos. Escala cuando
          tu clinica lo necesite.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
          {/* Primary CTA */}
          <Button
            size="lg"
            className="bg-white text-primary-700 font-semibold hover:bg-primary-50 dark:bg-white dark:text-primary-700 dark:hover:bg-primary-50 shadow-lg shadow-primary-900/30 transition-colors duration-150"
            asChild
          >
            <Link href="/register">
              Empezar gratis
              <ArrowRight className="ml-1 w-4 h-4" aria-hidden="true" />
            </Link>
          </Button>

          {/* Sales CTA */}
          <Button
            size="lg"
            variant="outline"
            className="border-white/50 text-white bg-transparent hover:bg-white/10 hover:text-white dark:border-white/50 dark:text-white dark:hover:bg-white/10 transition-colors duration-150"
            asChild
          >
            <Link href="mailto:ventas@dentalos.co">
              <Phone className="mr-1.5 w-4 h-4" aria-hidden="true" />
              Hablar con ventas
            </Link>
          </Button>
        </div>

        {/* Trust signals */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-x-8 gap-y-2 text-primary-100">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span className="text-sm">Datos seguros — Ley 1581 Colombia</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span className="text-sm">14 dias de prueba en todos los planes</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span className="text-sm">Cancela cuando quieras</span>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function PricingPage() {
  return (
    <>
      {/*
        PricingCards renders the full hero + billing toggle + plan cards.
        It includes pt-24 internally for fixed navbar clearance.
      */}
      <PricingCards />

      {/* Feature comparison matrix */}
      <PricingTable />

      {/* AI add-ons */}
      <PricingAddons />

      {/* FAQ accordion */}
      <FaqSection />

      {/* Bottom CTA */}
      <PricingCta />
    </>
  );
}
