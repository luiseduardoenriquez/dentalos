"use client";

import * as React from "react";
import { Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useAvailablePlans,
  useChangePlan,
  type AvailablePlanItem,
} from "@/lib/hooks/use-settings";

// ─── Types ───────────────────────────────────────────────────────────────────

type BillingCycle = "monthly" | "annual";

interface UpgradePlanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ─── Feature Labels ──────────────────────────────────────────────────────────

const KEY_FEATURES: Record<string, string[]> = {
  free: [
    "1 doctor",
    "Hasta 50 pacientes",
    "Odontograma básico",
    "Agenda",
    "Soporte por comunidad",
  ],
  starter: [
    "Pacientes ilimitados",
    "Historia clínica completa",
    "Facturación básica",
    "Consentimientos digitales",
    "Prescripciones",
    "Soporte por email",
  ],
  pro: [
    "Todo Starter incluido",
    "RIPS automático",
    "Facturación electrónica DIAN",
    "Portal del paciente",
    "Reportes y analítica",
    "Firma digital legal",
    "Soporte prioritario",
  ],
  clinica: [
    "Todo Pro incluido",
    "3 doctores incluidos",
    "Multi-sede en un dashboard",
    "Inventario y esterilización",
    "Roles y permisos avanzados",
    "API de integración",
  ],
  enterprise: [
    "Todo Clínica incluido",
    "SLA garantizado",
    "Migración dedicada",
    "Integraciones personalizadas",
    "Soporte 24/7",
  ],
};

// ─── Price Display ───────────────────────────────────────────────────────────

function PlanPrice({ plan, billing }: { plan: AvailablePlanItem; billing: BillingCycle }) {
  if (plan.slug === "enterprise") {
    return (
      <div className="mt-2 mb-1">
        <span className="text-xl font-bold text-foreground">Personalizado</span>
      </div>
    );
  }

  if (plan.price_cents === 0) {
    return (
      <div className="mt-2 mb-1">
        <span className="text-2xl font-bold text-foreground">$0</span>
        <span className="text-xs text-[hsl(var(--muted-foreground))] ml-1">para siempre</span>
      </div>
    );
  }

  const monthlyPrice = plan.price_cents / 100;
  const annualMonthlyRate = Math.floor((monthlyPrice * 10) / 12);
  const displayPrice = billing === "annual" ? annualMonthlyRate : monthlyPrice;
  const unit = plan.pricing_model === "per_location" ? "/sede/mes" : "/doctor/mes";

  return (
    <div className="mt-2 mb-1">
      {billing === "annual" && (
        <span className="text-xs line-through text-[hsl(var(--muted-foreground))] mr-1">
          ${monthlyPrice}
        </span>
      )}
      <span className="text-2xl font-bold text-foreground">${displayPrice}</span>
      <span className="text-xs text-[hsl(var(--muted-foreground))] ml-1">{unit}</span>
    </div>
  );
}

// ─── Plan Card ───────────────────────────────────────────────────────────────

function UpgradePlanCard({
  plan,
  billing,
  isCurrent,
  isChanging,
  onSelect,
}: {
  plan: AvailablePlanItem;
  billing: BillingCycle;
  isCurrent: boolean;
  isChanging: boolean;
  onSelect: (plan: AvailablePlanItem) => void;
}) {
  const isEnterprise = plan.slug === "enterprise";
  const isPro = plan.slug === "pro";
  const features = KEY_FEATURES[plan.slug] ?? [];

  return (
    <div
      className={cn(
        "relative flex flex-col rounded-xl border p-4 transition-shadow",
        isCurrent
          ? "border-primary-600 ring-2 ring-primary-600/20 bg-primary-50/50 dark:bg-primary-900/10"
          : isPro
            ? "border-primary-300 dark:border-primary-700 shadow-md"
            : "hover:shadow-md",
      )}
    >
      {/* Badges */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-bold text-foreground">{plan.name}</span>
        {isCurrent && (
          <Badge variant="default" className="text-[10px] px-1.5 py-0">
            Plan actual
          </Badge>
        )}
        {isPro && !isCurrent && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            Más popular
          </Badge>
        )}
      </div>

      <PlanPrice plan={plan} billing={billing} />

      {/* Features */}
      <ul className="mt-3 space-y-1.5 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-xs text-[hsl(var(--muted-foreground))]">
            <Check className="mt-0.5 h-3 w-3 shrink-0 text-primary-600" aria-hidden />
            {f}
          </li>
        ))}
      </ul>

      {/* Limits summary */}
      {!isEnterprise && (
        <p className="mt-3 text-[10px] text-[hsl(var(--muted-foreground))] border-t pt-2">
          {plan.max_patients <= 0 ? "Pacientes ilimitados" : `${plan.max_patients} pacientes`}
          {" · "}
          {plan.max_doctors <= 0 ? "Doctores ilimitados" : `${plan.max_doctors} doctores`}
        </p>
      )}

      {/* CTA */}
      <div className="mt-3">
        {isCurrent ? (
          <Button variant="outline" size="sm" className="w-full" disabled>
            Plan actual
          </Button>
        ) : isEnterprise ? (
          <Button variant="outline" size="sm" className="w-full" asChild>
            <a href="mailto:ventas@dentalos.co">Contactar ventas</a>
          </Button>
        ) : (
          <Button
            size="sm"
            className="w-full"
            disabled={isChanging}
            onClick={() => onSelect(plan)}
          >
            Seleccionar
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Billing Toggle ──────────────────────────────────────────────────────────

function BillingToggle({
  billing,
  onChange,
}: {
  billing: BillingCycle;
  onChange: (cycle: BillingCycle) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-2" role="group" aria-label="Ciclo de facturación">
      <button
        type="button"
        onClick={() => onChange("monthly")}
        className={cn(
          "text-xs font-medium transition-colors px-1",
          billing === "monthly"
            ? "text-foreground"
            : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
        )}
        aria-pressed={billing === "monthly"}
      >
        Mensual
      </button>

      <button
        type="button"
        role="switch"
        aria-checked={billing === "annual"}
        aria-label="Cambiar a facturación anual"
        onClick={() => onChange(billing === "monthly" ? "annual" : "monthly")}
        className={cn(
          "relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
          billing === "annual"
            ? "bg-primary-600"
            : "bg-[hsl(var(--muted))]",
        )}
      >
        <span
          className={cn(
            "inline-block h-3 w-3 transform rounded-full bg-white shadow transition-transform duration-200",
            billing === "annual" ? "translate-x-5" : "translate-x-1",
          )}
        />
      </button>

      <button
        type="button"
        onClick={() => onChange("annual")}
        className={cn(
          "text-xs font-medium transition-colors px-1 flex items-center gap-1",
          billing === "annual"
            ? "text-foreground"
            : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
        )}
        aria-pressed={billing === "annual"}
      >
        Anual
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
          -17%
        </Badge>
      </button>
    </div>
  );
}

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function PlansSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="rounded-xl border p-4 space-y-3">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-8 w-24" />
          <div className="space-y-2">
            {[1, 2, 3, 4].map((j) => (
              <Skeleton key={j} className="h-3 w-full" />
            ))}
          </div>
          <Skeleton className="h-8 w-full" />
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function UpgradePlanDialog({ open, onOpenChange }: UpgradePlanDialogProps) {
  const [billing, setBilling] = React.useState<BillingCycle>("monthly");
  const [confirmPlan, setConfirmPlan] = React.useState<AvailablePlanItem | null>(null);

  const { data, isLoading } = useAvailablePlans(open);
  const { mutate: changePlan, isPending: isChanging } = useChangePlan();

  function handleSelect(plan: AvailablePlanItem) {
    setConfirmPlan(plan);
  }

  function handleConfirm() {
    if (!confirmPlan) return;
    changePlan(confirmPlan.id, {
      onSuccess: () => {
        setConfirmPlan(null);
        onOpenChange(false);
      },
      onSettled: () => {
        setConfirmPlan(null);
      },
    });
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Actualizar plan</DialogTitle>
            <DialogDescription>
              Elige el plan que mejor se adapte a tu clínica. El cambio se aplica inmediatamente.
            </DialogDescription>
          </DialogHeader>

          <BillingToggle billing={billing} onChange={setBilling} />

          {isLoading ? (
            <PlansSkeleton />
          ) : data ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
              {data.plans.map((plan) => (
                <UpgradePlanCard
                  key={plan.id}
                  plan={plan}
                  billing={billing}
                  isCurrent={plan.slug === data.current_plan_slug}
                  isChanging={isChanging}
                  onSelect={handleSelect}
                />
              ))}
            </div>
          ) : null}

          <p className="mt-4 text-center text-xs text-[hsl(var(--muted-foreground))]">
            Todos los precios en USD. El cambio se aplica inmediatamente a tu suscripción.
          </p>
        </DialogContent>
      </Dialog>

      {/* Confirmation dialog */}
      <AlertDialog open={!!confirmPlan} onOpenChange={(open) => !open && setConfirmPlan(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cambiar al plan {confirmPlan?.name}</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmPlan && confirmPlan.price_cents > 0
                ? `Tu plan cambiará a ${confirmPlan.name} por $${confirmPlan.price_cents / 100} USD/${confirmPlan.pricing_model === "per_location" ? "sede" : "doctor"}/mes. El cambio se aplica inmediatamente.`
                : `Tu plan cambiará a ${confirmPlan?.name}. Algunas funciones pueden dejar de estar disponibles.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isChanging}>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm} disabled={isChanging}>
              {isChanging ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Cambiando...
                </>
              ) : (
                "Confirmar cambio"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
