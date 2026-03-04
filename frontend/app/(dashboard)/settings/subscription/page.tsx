"use client";

import * as React from "react";
import { Zap, Users, User, HardDrive, UserCheck, Mic, Image } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { useUsage, usePlanLimits, useAddons, useToggleAddon } from "@/lib/hooks/use-settings";
import { useAuth } from "@/lib/hooks/use-auth";
import { useToast } from "@/lib/hooks/use-toast";
import { formatCurrency } from "@/lib/utils";

// ─── Usage Bar ────────────────────────────────────────────────────────────────

interface UsageBarProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  current: number;
  max: number;
  unit?: string;
}

function UsageBar({ icon: Icon, label, current, max, unit = "" }: UsageBarProps) {
  const isUnlimited = max <= 0;
  const percentage = isUnlimited ? 0 : Math.min((current / max) * 100, 100);

  const barColor =
    percentage >= 90
      ? "bg-destructive-500"
      : percentage >= 70
        ? "bg-accent-500"
        : "bg-primary-600";

  const badgeVariant =
    percentage >= 90 ? "destructive" : percentage >= 70 ? "warning" : "success";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          <span className="text-sm font-medium text-foreground">{label}</span>
        </div>
        {isUnlimited ? (
          <Badge variant="success">Ilimitado</Badge>
        ) : (
          <Badge variant={badgeVariant}>
            {current.toLocaleString("es-CO")} / {max.toLocaleString("es-CO")}{unit}
          </Badge>
        )}
      </div>

      {!isUnlimited && (
        <div className="h-2 w-full rounded-full bg-[hsl(var(--muted))] overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${percentage}%` }}
            role="progressbar"
            aria-valuenow={current}
            aria-valuemin={0}
            aria-valuemax={max}
            aria-label={`${label}: ${current} de ${max}${unit}`}
          />
        </div>
      )}

      {!isUnlimited && (
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          {isUnlimited
            ? "Sin límite"
            : `${Math.max(0, max - current).toLocaleString("es-CO")} disponible${max - current !== 1 ? "s" : ""}${unit}`}
        </p>
      )}
    </div>
  );
}

// ─── Plan Features ────────────────────────────────────────────────────────────

const FEATURE_LABELS: Record<string, string> = {
  odontogram_classic: "Odontograma clásico",
  odontogram_anatomic: "Odontograma anatómico",
  clinical_records: "Historia clínica",
  treatment_plans: "Planes de tratamiento",
  consents_digital: "Consentimientos digitales",
  prescriptions: "Recetas digitales",
  appointments: "Agenda",
  billing: "Facturación",
  patient_portal: "Portal del paciente",
  whatsapp_notifications: "Notificaciones WhatsApp",
  analytics_basic: "Analíticas básicas",
  analytics_advanced: "Analíticas avanzadas",
  rips_reporting: "Generación de RIPS",
  electronic_invoicing: "Facturación electrónica DIAN",
  inventory_module: "Inventario y esterilización",
  multi_location: "Multi-sede",
  api_access: "API de integración",
  telehealth: "Telemedicina",
};

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function SubscriptionSkeleton() {
  return (
    <div className="max-w-2xl space-y-6">
      <div className="space-y-1">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-64" />
      </div>
      <div className="border rounded-xl p-6 space-y-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-10 w-24" />
        <div className="grid grid-cols-2 gap-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
      </div>
      <div className="border rounded-xl p-6 space-y-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-2 w-full rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Addon Definitions ───────────────────────────────────────────────────────

interface AddonDef {
  key: string;
  label: string;
  description: string;
  price: string;
  icon: React.ComponentType<{ className?: string }>;
}

const ADDONS: AddonDef[] = [
  {
    key: "voice_dictation",
    label: "AI Voz",
    description: "Dictado clínico por voz con IA. Aplique hallazgos al odontograma automáticamente.",
    price: "$10 USD / doctor / mes",
    icon: Mic,
  },
  {
    key: "radiograph_ai",
    label: "AI Radiografía",
    description: "Análisis de radiografías con inteligencia artificial para detección asistida.",
    price: "$20 USD / doctor / mes",
    icon: Image,
  },
];

// ─── Addon Card ──────────────────────────────────────────────────────────────

interface AddonCardProps {
  addon: AddonDef;
  enabled: boolean;
  isPending: boolean;
  onToggle: (key: string, enabled: boolean) => void;
}

function AddonCard({ addon, enabled, isPending, onToggle }: AddonCardProps) {
  const Icon = addon.icon;

  return (
    <div className="flex items-start gap-4 rounded-lg border p-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
        <Icon className="h-5 w-5 text-primary-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-foreground">{addon.label}</p>
          {enabled && <Badge variant="success">Activo</Badge>}
        </div>
        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
          {addon.description}
        </p>
        <p className="text-xs font-medium text-primary-600 mt-1">{addon.price}</p>
      </div>
      <Button
        size="sm"
        variant={enabled ? "outline" : "default"}
        disabled={isPending}
        onClick={() => onToggle(addon.key, !enabled)}
        className="shrink-0"
      >
        {isPending ? "..." : enabled ? "Desactivar" : "Activar"}
      </Button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SubscriptionPage() {
  const { info } = useToast();
  const { has_role } = useAuth();

  const { data: usage, isLoading: isLoadingUsage } = useUsage();
  const { data: limits, isLoading: isLoadingLimits } = usePlanLimits();
  const { data: addonsData, isLoading: isLoadingAddons } = useAddons();
  const { mutate: toggleAddon, isPending: isTogglingAddon } = useToggleAddon();

  const isLoading = isLoadingUsage || isLoadingLimits || isLoadingAddons;

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = React.useState<{
    open: boolean;
    addonKey: string;
    addonLabel: string;
    addonPrice: string;
    enabling: boolean;
  }>({ open: false, addonKey: "", addonLabel: "", addonPrice: "", enabling: false });

  function handleAddonToggle(key: string, enabled: boolean) {
    const addon = ADDONS.find((a) => a.key === key);
    if (!addon) return;

    setConfirmDialog({
      open: true,
      addonKey: key,
      addonLabel: addon.label,
      addonPrice: addon.price,
      enabling: enabled,
    });
  }

  function handleConfirmAddon() {
    toggleAddon(
      { addon: confirmDialog.addonKey, enabled: confirmDialog.enabling },
      { onSettled: () => setConfirmDialog((prev) => ({ ...prev, open: false })) },
    );
  }

  function handleUpgrade() {
    info("Próximamente", "La actualización de plan estará disponible muy pronto.");
  }

  if (isLoading) {
    return <SubscriptionSkeleton />;
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* ─── Page Header ──────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Plan y uso</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Revisa tu plan actual y el uso de recursos de la clínica.
        </p>
      </div>

      {/* ─── Current Plan Card ────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-base">Plan actual</CardTitle>
              <CardDescription>
                Tu suscripción activa y características incluidas.
              </CardDescription>
            </div>
            <Badge variant="default" className="shrink-0 capitalize">
              {limits?.plan_name ?? "Free"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Price */}
          <div>
            {limits?.plan_price_monthly_cents && limits.plan_price_monthly_cents > 0 ? (
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold text-foreground">
                  {formatCurrency(limits.plan_price_monthly_cents)}
                </span>
                <span className="text-sm text-[hsl(var(--muted-foreground))]">/ doctor / mes</span>
              </div>
            ) : (
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold text-foreground">Gratis</span>
              </div>
            )}
          </div>

          {/* Features */}
          {limits?.features && Object.keys(limits.features).filter((k) => limits.features[k]).length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mb-3">
                Incluido en tu plan
              </p>
              <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {Object.keys(limits.features).filter((k) => limits.features[k]).map((feature) => (
                  <div key={feature} className="flex items-center gap-2 text-sm text-foreground">
                    <div className="h-1.5 w-1.5 rounded-full bg-primary-600 shrink-0" />
                    {FEATURE_LABELS[feature] ?? feature}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upgrade CTA */}
          <div className="pt-2 border-t border-[hsl(var(--border))]">
            <Button onClick={handleUpgrade} className="w-full sm:w-auto">
              <Zap className="mr-2 h-4 w-4" />
              Actualizar plan
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ─── Usage Card ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Uso actual</CardTitle>
          <CardDescription>
            Recursos utilizados en la clínica durante el período vigente.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <UsageBar
            icon={Users}
            label="Pacientes"
            current={usage?.patients_count ?? 0}
            max={limits?.max_patients ?? 0}
          />

          <UsageBar
            icon={UserCheck}
            label="Doctores"
            current={usage?.doctors_count ?? 0}
            max={limits?.max_doctors ?? 0}
          />

          <UsageBar
            icon={User}
            label="Usuarios totales"
            current={usage?.users_count ?? 0}
            max={limits?.max_users ?? 0}
          />

          <UsageBar
            icon={HardDrive}
            label="Almacenamiento"
            current={usage?.storage_used_mb ?? 0}
            max={limits?.max_storage_mb ?? 0}
            unit=" MB"
          />
        </CardContent>
      </Card>

      {/* ─── Complementos (Add-ons) ───────────────────────────────────── */}
      {has_role("clinic_owner") && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Complementos</CardTitle>
            <CardDescription>
              Activa funciones avanzadas de inteligencia artificial para tu clínica.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {ADDONS.map((addon) => (
              <AddonCard
                key={addon.key}
                addon={addon}
                enabled={addonsData?.addons[addon.key] === true}
                isPending={isTogglingAddon}
                onToggle={handleAddonToggle}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Addon confirmation dialog */}
      <AlertDialog
        open={confirmDialog.open}
        onOpenChange={(open) => setConfirmDialog((prev) => ({ ...prev, open }))}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmDialog.enabling ? "Activar" : "Desactivar"} {confirmDialog.addonLabel}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmDialog.enabling
                ? `Se activará ${confirmDialog.addonLabel} por ${confirmDialog.addonPrice}. El cargo se reflejará en tu próxima factura.`
                : `Se desactivará ${confirmDialog.addonLabel}. Esta función dejará de estar disponible para todos los usuarios de la clínica.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isTogglingAddon}>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmAddon} disabled={isTogglingAddon}>
              {isTogglingAddon ? "Procesando..." : confirmDialog.enabling ? "Activar" : "Desactivar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ─── Upgrade Prompt (when nearing limits) ─────────────────────── */}
      {usage && limits && limits.max_patients > 0 && (
        <div className="rounded-xl border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20 p-4">
          <div className="flex items-start gap-3">
            <Zap className="h-5 w-5 text-primary-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-primary-900 dark:text-primary-100">
                Desbloquea todo el potencial de DentalOS
              </p>
              <p className="text-sm text-primary-700 dark:text-primary-300 mt-0.5">
                Actualiza tu plan para acceder a más pacientes, usuarios y funciones avanzadas
                como facturación DIAN, RIPS y dictado por voz.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={handleUpgrade}
              >
                Ver planes disponibles
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
