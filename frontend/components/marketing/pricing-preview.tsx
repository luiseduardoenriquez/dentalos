import Link from "next/link";
import { CheckCircle, ArrowRight } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PricingTier {
  name: string;
  /** Monthly price in USD. null = free */
  price: number | null;
  priceSuffix: string;
  tagline: string;
  features: string[];
  cta: string;
  ctaHref: string;
  highlighted: boolean;
  badge?: string;
}

const TIERS: PricingTier[] = [
  {
    name: "Gratis",
    price: null,
    priceSuffix: "para siempre",
    tagline: "Para clinicas que recien empiezan.",
    features: [
      "1 doctor incluido",
      "Hasta 50 pacientes activos",
      "Odontograma digital basico",
      "Agenda de citas",
    ],
    cta: "Crear cuenta gratis",
    ctaHref: "/register",
    highlighted: false,
  },
  {
    name: "Starter",
    price: 19,
    priceSuffix: "/ doctor / mes",
    tagline: "Para clinicas en crecimiento.",
    features: [
      "Pacientes ilimitados",
      "Historia clinica completa",
      "Facturacion DIAN incluida",
      "Reportes RIPS automaticos",
    ],
    cta: "Empieza gratis 14 dias",
    ctaHref: "/register?plan=starter",
    highlighted: true,
    badge: "Mas popular",
  },
  {
    name: "Pro",
    price: 39,
    priceSuffix: "/ doctor / mes",
    tagline: "Para clinicas que quieren lo mejor.",
    features: [
      "Todo lo de Starter",
      "Portal del paciente",
      "Mensajeria y recordatorios",
      "Soporte prioritario",
    ],
    cta: "Empieza gratis 14 dias",
    ctaHref: "/register?plan=pro",
    highlighted: false,
  },
];

// ─── Pricing Preview Section ──────────────────────────────────────────────────

export function PricingPreviewSection() {
  return (
    <section className="py-16 md:py-24 bg-slate-50 dark:bg-zinc-900/50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

        {/* Section header */}
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-zinc-50">
            Planes simples, sin sorpresas
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-500 dark:text-zinc-400">
            Todos los planes incluyen onboarding gratuito y soporte en espanol.
            Sin contratos anuales obligatorios.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {TIERS.map((tier) => (
            <PricingCard key={tier.name} tier={tier} />
          ))}
        </div>

        {/* Link to full pricing page */}
        <div className="mt-10 text-center">
          <Link
            href="/pricing"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 transition-colors"
          >
            Ver todos los planes y comparar funciones
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─── Pricing Card ─────────────────────────────────────────────────────────────

function PricingCard({ tier }: { tier: PricingTier }) {
  const isHighlighted = tier.highlighted;

  return (
    <Card
      className={cn(
        "relative flex flex-col",
        isHighlighted
          ? "border-2 border-primary-600 dark:border-primary-500 shadow-lg shadow-primary-100 dark:shadow-primary-950/40"
          : "border border-[hsl(var(--border))]",
      )}
    >
      {/* Popular badge */}
      {tier.badge && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-primary-600 text-white shadow-sm">
            {tier.badge}
          </span>
        </div>
      )}

      <CardHeader className={cn("pb-4", isHighlighted && "pt-8")}>
        <CardTitle className="text-lg font-bold text-slate-900 dark:text-zinc-50">
          {tier.name}
        </CardTitle>
        <CardDescription className="text-sm">
          {tier.tagline}
        </CardDescription>

        {/* Price display */}
        <div className="mt-4 flex items-end gap-1">
          {tier.price === null ? (
            <>
              <span className="text-4xl font-extrabold text-slate-900 dark:text-zinc-50">
                $0
              </span>
              <span className="mb-1 text-sm text-slate-500 dark:text-zinc-400">
                {tier.priceSuffix}
              </span>
            </>
          ) : (
            <>
              <span className="text-xs text-slate-500 dark:text-zinc-400 mb-2 mr-0.5">
                USD
              </span>
              <span className="text-4xl font-extrabold text-slate-900 dark:text-zinc-50">
                ${tier.price}
              </span>
              <span className="mb-1 text-sm text-slate-500 dark:text-zinc-400">
                {tier.priceSuffix}
              </span>
            </>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col flex-1 gap-6">
        {/* Feature list */}
        <ul className="space-y-2.5 flex-1">
          {tier.features.map((feature) => (
            <li key={feature} className="flex items-center gap-2.5">
              <CheckCircle
                className="w-4 h-4 shrink-0 text-green-500"
                aria-hidden="true"
              />
              <span className="text-sm text-slate-600 dark:text-zinc-300">
                {feature}
              </span>
            </li>
          ))}
        </ul>

        {/* CTA button */}
        <Button
          variant={isHighlighted ? "default" : "outline"}
          className="w-full"
          asChild
        >
          <Link href={tier.ctaHref}>{tier.cta}</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
