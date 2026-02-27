"use client";

import { useState } from "react";
import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type BillingCycle = "monthly" | "annual";

interface PlanConfig {
  id: string;
  name: string;
  monthlyPrice: number | null; // null = contact sales
  currency: string;
  unit: string;
  description: string;
  features: string[];
  cta: string;
  ctaHref: string;
  ctaVariant: "default" | "outline" | "ghost";
  highlighted: boolean;
  badge: string | null;
}

// ─── Plan Data ────────────────────────────────────────────────────────────────

const PLANS: PlanConfig[] = [
  {
    id: "gratis",
    name: "Gratis",
    monthlyPrice: 0,
    currency: "USD",
    unit: "",
    description: "Para empezar sin riesgo. Sin tarjeta de credito.",
    features: [
      "1 doctor",
      "Hasta 50 pacientes",
      "Odontograma basico",
      "Agenda",
      "Soporte por comunidad",
    ],
    cta: "Empezar gratis",
    ctaHref: "/register",
    ctaVariant: "ghost",
    highlighted: false,
    badge: null,
  },
  {
    id: "starter",
    name: "Starter",
    monthlyPrice: 19,
    currency: "USD",
    unit: "/doctor/mes",
    description: "Para consultorios en crecimiento que necesitan mas.",
    features: [
      "Pacientes ilimitados",
      "Historia clinica completa",
      "Facturacion basica",
      "Consentimientos digitales",
      "Prescripciones",
      "Soporte por email",
    ],
    cta: "Empezar prueba",
    ctaHref: "/register?plan=starter",
    ctaVariant: "default",
    highlighted: false,
    badge: null,
  },
  {
    id: "pro",
    name: "Pro",
    monthlyPrice: 39,
    currency: "USD",
    unit: "/doctor/mes",
    description: "Para clinicas que exigen cumplimiento y automatizacion total.",
    features: [
      "Todo Starter incluido",
      "RIPS automatico",
      "Facturacion electronica DIAN",
      "Portal del paciente",
      "Reportes y analitica",
      "Firma digital legal",
      "Soporte prioritario",
    ],
    cta: "Empezar prueba",
    ctaHref: "/register?plan=pro",
    ctaVariant: "default",
    highlighted: true,
    badge: "Mas popular",
  },
  {
    id: "clinica",
    name: "Clinica",
    monthlyPrice: 69,
    currency: "USD",
    unit: "/sede/mes",
    description: "Para clinicas con multiples sedes y equipos grandes.",
    features: [
      "Todo Pro incluido",
      "3 doctores incluidos",
      "Multi-sede en un dashboard",
      "Inventario y esterilizacion",
      "Roles y permisos avanzados",
      "API de integracion",
      "Soporte prioritario",
    ],
    cta: "Empezar prueba",
    ctaHref: "/register?plan=clinica",
    ctaVariant: "default",
    highlighted: false,
    badge: null,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    monthlyPrice: null,
    currency: "USD",
    unit: "",
    description: "Para redes de clinicas que necesitan control total.",
    features: [
      "Todo Clinica incluido",
      "SLA garantizado",
      "Migracion dedicada",
      "Integraciones personalizadas",
      "Soporte 24/7",
      "Facturacion personalizada",
      "Gerente de cuenta dedicado",
    ],
    cta: "Contactar ventas",
    ctaHref: "mailto:ventas@dentalos.co",
    ctaVariant: "outline",
    highlighted: false,
    badge: null,
  },
];

// ─── Price Display ─────────────────────────────────────────────────────────────

function PriceDisplay({
  plan,
  billing,
}: {
  plan: PlanConfig;
  billing: BillingCycle;
}) {
  if (plan.monthlyPrice === null) {
    return (
      <div className="mt-4 mb-1">
        <span className="text-2xl font-bold text-slate-900 dark:text-zinc-100">
          Personalizado
        </span>
      </div>
    );
  }

  if (plan.monthlyPrice === 0) {
    return (
      <div className="mt-4 mb-1">
        <span className="text-4xl font-bold text-slate-900 dark:text-zinc-100">
          $0
        </span>
        <span className="text-sm text-slate-500 dark:text-zinc-500 ml-1">
          para siempre
        </span>
      </div>
    );
  }

  // Annual price = monthly * 10 (2 months free = 10 months price for 12)
  const annualMonthlyRate = Math.floor((plan.monthlyPrice * 10) / 12);
  const displayPrice =
    billing === "annual" ? annualMonthlyRate : plan.monthlyPrice;

  return (
    <div className="mt-4 mb-1">
      {billing === "annual" && (
        <span className="text-sm line-through text-slate-400 dark:text-zinc-600 mr-2">
          ${plan.monthlyPrice}
        </span>
      )}
      <span className="text-4xl font-bold text-slate-900 dark:text-zinc-100">
        ${displayPrice}
      </span>
      <span className="text-sm text-slate-500 dark:text-zinc-500 ml-1">
        {plan.unit}
      </span>
    </div>
  );
}

// ─── Single Plan Card ──────────────────────────────────────────────────────────

function PlanCard({
  plan,
  billing,
}: {
  plan: PlanConfig;
  billing: BillingCycle;
}) {
  return (
    <Card
      className={cn(
        "relative flex flex-col transition-shadow duration-200",
        plan.highlighted
          ? "border-2 border-primary-600 ring-4 ring-primary-600/10 shadow-xl dark:ring-primary-500/20"
          : "hover:shadow-md",
      )}
    >
      {/* Popular badge */}
      {plan.badge && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <Badge className="px-3 py-1 text-xs font-semibold shadow-sm">
            {plan.badge}
          </Badge>
        </div>
      )}

      <CardHeader className="pb-2">
        <CardTitle className="text-xl font-bold text-slate-900 dark:text-zinc-100">
          {plan.name}
        </CardTitle>
        <PriceDisplay plan={plan} billing={billing} />
        <CardDescription className="text-sm leading-relaxed">
          {plan.description}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 pt-4">
        <ul className="space-y-2.5" aria-label={`Funciones del plan ${plan.name}`}>
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2.5">
              <Check
                className="mt-0.5 h-4 w-4 shrink-0 text-primary-600 dark:text-primary-400"
                aria-hidden="true"
              />
              <span className="text-sm text-slate-700 dark:text-zinc-300">
                {feature}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>

      <CardFooter className="pt-6">
        <Button
          variant={plan.ctaVariant}
          size="lg"
          className="w-full font-semibold"
          asChild
        >
          <Link href={plan.ctaHref}>{plan.cta}</Link>
        </Button>
      </CardFooter>
    </Card>
  );
}

// ─── Billing Toggle ────────────────────────────────────────────────────────────

function BillingToggle({
  billing,
  onChange,
}: {
  billing: BillingCycle;
  onChange: (cycle: BillingCycle) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-3" role="group" aria-label="Ciclo de facturacion">
      <button
        type="button"
        onClick={() => onChange("monthly")}
        className={cn(
          "text-sm font-medium transition-colors duration-150 px-1",
          billing === "monthly"
            ? "text-slate-900 dark:text-zinc-100"
            : "text-slate-400 dark:text-zinc-500 hover:text-slate-700 dark:hover:text-zinc-300",
        )}
        aria-pressed={billing === "monthly"}
      >
        Mensual
      </button>

      {/* Toggle switch */}
      <button
        type="button"
        role="switch"
        aria-checked={billing === "annual"}
        aria-label="Cambiar a facturacion anual"
        onClick={() => onChange(billing === "monthly" ? "annual" : "monthly")}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
          billing === "annual"
            ? "bg-primary-600"
            : "bg-slate-200 dark:bg-zinc-700",
        )}
      >
        <span
          className={cn(
            "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200",
            billing === "annual" ? "translate-x-6" : "translate-x-1",
          )}
        />
      </button>

      <button
        type="button"
        onClick={() => onChange("annual")}
        className={cn(
          "text-sm font-medium transition-colors duration-150 px-1 flex items-center gap-2",
          billing === "annual"
            ? "text-slate-900 dark:text-zinc-100"
            : "text-slate-400 dark:text-zinc-500 hover:text-slate-700 dark:hover:text-zinc-300",
        )}
        aria-pressed={billing === "annual"}
      >
        Anual
        <Badge variant="secondary" className="text-xs font-semibold">
          Ahorra 2 meses
        </Badge>
      </button>
    </div>
  );
}

// ─── Main Export ───────────────────────────────────────────────────────────────

export function PricingCards() {
  const [billing, setBilling] = useState<BillingCycle>("monthly");

  return (
    <section
      className="pt-24 pb-16 px-4 sm:px-6 lg:px-8 bg-white dark:bg-zinc-950"
      aria-labelledby="pricing-heading"
    >
      <div className="mx-auto max-w-7xl">
        {/* Section header */}
        <div className="text-center mb-12">
          <h1
            id="pricing-heading"
            className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-zinc-50"
          >
            Precios simples y transparentes
          </h1>
          <p className="mt-4 text-lg text-slate-600 dark:text-zinc-400 max-w-2xl mx-auto">
            Sin contratos ocultos. Sin sorpresas. Escala segun crece tu clinica.
            Todos los planes incluyen 14 dias de prueba gratis.
          </p>

          {/* Billing toggle */}
          <div className="mt-8">
            <BillingToggle billing={billing} onChange={setBilling} />
          </div>
        </div>

        {/* Plan cards grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 items-start">
          {PLANS.map((plan) => (
            <PlanCard key={plan.id} plan={plan} billing={billing} />
          ))}
        </div>

        {/* Footer note */}
        <p className="mt-10 text-center text-sm text-slate-500 dark:text-zinc-500">
          Todos los precios en USD. Impuestos colombianos (IVA) pueden aplicar.{" "}
          <Link
            href="mailto:ventas@dentalos.co"
            className="text-primary-600 dark:text-primary-400 hover:underline underline-offset-4"
          >
            Contactanos para precios en COP.
          </Link>
        </p>
      </div>
    </section>
  );
}
