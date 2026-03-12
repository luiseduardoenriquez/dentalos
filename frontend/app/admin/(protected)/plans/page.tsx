"use client";

import * as React from "react";
import {
  useAdminPlans,
  useUpdatePlan,
  usePlanChangeHistory,
  type PlanResponse,
  type PlanUpdatePayload,
  type PlanChangeHistoryEntry,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

function formatPricingModel(pricingModel: string): string {
  if (pricingModel === "per_doctor") return "Por doctor";
  if (pricingModel === "flat") return "Tarifa plana";
  return pricingModel;
}

function formatDateTime(isoString: string): string {
  try {
    return new Intl.DateTimeFormat("es-CO", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}

// ─── Skeleton Grid ─────────────────────────────────────────────────────────────

function PlansLoadingSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardHeader className="pb-3">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-20 mt-1" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-9 w-20 mt-2" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Plan History Modal ────────────────────────────────────────────────────────

interface PlanHistoryModalProps {
  plan: PlanResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function PlanHistoryModal({ plan, open, onOpenChange }: PlanHistoryModalProps) {
  // enabled is gated on open so the query only fires when the modal is visible
  const { data, isLoading, isError } = usePlanChangeHistory(
    open ? plan.id : "",
  );

  const entries: PlanChangeHistoryEntry[] = data?.items ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Historial de cambios: {plan.name}</DialogTitle>
          <DialogDescription>
            Registro de todas las modificaciones realizadas a este plan.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[420px] overflow-y-auto">
          {isLoading && (
            <div className="space-y-2 py-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          )}

          {isError && (
            <p className="py-8 text-center text-sm text-[hsl(var(--muted-foreground))]">
              Error al cargar el historial. Intenta de nuevo.
            </p>
          )}

          {!isLoading && !isError && entries.length === 0 && (
            <p className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
              Sin cambios registrados
            </p>
          )}

          {!isLoading && !isError && entries.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))]">
                  <th className="py-2 pr-4 text-left font-semibold text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                    Fecha
                  </th>
                  <th className="py-2 pr-4 text-left font-semibold text-[hsl(var(--muted-foreground))]">
                    Campo cambiado
                  </th>
                  <th className="py-2 pr-4 text-left font-semibold text-[hsl(var(--muted-foreground))]">
                    Valor anterior
                  </th>
                  <th className="py-2 text-left font-semibold text-[hsl(var(--muted-foreground))]">
                    Valor nuevo
                  </th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-[hsl(var(--border))] last:border-0"
                  >
                    <td className="py-2 pr-4 text-xs text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                      {formatDateTime(entry.created_at)}
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs">
                      {entry.field_changed}
                    </td>
                    <td className="py-2 pr-4 text-xs text-[hsl(var(--muted-foreground))]">
                      {entry.old_value ?? (
                        <span className="italic">vacío</span>
                      )}
                    </td>
                    <td className="py-2 text-xs font-medium text-foreground">
                      {entry.new_value ?? (
                        <span className="italic font-normal text-[hsl(var(--muted-foreground))]">
                          vacío
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Plan Dialog ──────────────────────────────────────────────────────────

interface EditPlanDialogProps {
  plan: PlanResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function EditPlanDialog({ plan, open, onOpenChange }: EditPlanDialogProps) {
  const { success, error } = useToast();
  const updatePlan = useUpdatePlan();

  // Local form state — initialized from the plan prop each time the dialog opens
  const [priceCents, setPriceCents] = React.useState(plan.price_cents);
  const [maxPatients, setMaxPatients] = React.useState(plan.max_patients);
  const [maxDoctors, setMaxDoctors] = React.useState(plan.max_doctors);
  const [isActive, setIsActive] = React.useState(plan.is_active);
  const [featuresJson, setFeaturesJson] = React.useState(
    JSON.stringify(plan.features, null, 2),
  );
  const [jsonError, setJsonError] = React.useState<string | null>(null);

  // Reset form fields when the dialog re-opens with a (possibly different) plan
  React.useEffect(() => {
    if (open) {
      setPriceCents(plan.price_cents);
      setMaxPatients(plan.max_patients);
      setMaxDoctors(plan.max_doctors);
      setIsActive(plan.is_active);
      setFeaturesJson(JSON.stringify(plan.features, null, 2));
      setJsonError(null);
    }
  }, [open, plan]);

  function handleFeaturesChange(value: string) {
    setFeaturesJson(value);
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch {
      setJsonError("JSON inválido. Corrija el formato antes de guardar.");
    }
  }

  function handleSave() {
    if (jsonError) return;

    let parsedFeatures: Record<string, unknown>;
    try {
      parsedFeatures = JSON.parse(featuresJson);
    } catch {
      setJsonError("JSON inválido. Corrija el formato antes de guardar.");
      return;
    }

    const payload: PlanUpdatePayload = {
      price_cents: priceCents,
      max_patients: maxPatients,
      max_doctors: maxDoctors,
      is_active: isActive,
      features: parsedFeatures,
    };

    updatePlan.mutate(
      { id: plan.id, payload },
      {
        onSuccess: () => {
          success("Plan actualizado", "Los cambios se guardaron correctamente.");
          onOpenChange(false);
        },
        onError: () => {
          error("Error al guardar", "No se pudo actualizar el plan. Intenta de nuevo.");
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Editar plan: {plan.name}</DialogTitle>
          <DialogDescription>
            Modifica los límites, precio y características del plan. Los cambios
            afectan a los nuevos suscriptores de inmediato.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          {/* Price */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="edit-price-cents">Precio (centavos)</Label>
              <Input
                id="edit-price-cents"
                type="number"
                min={0}
                value={priceCents}
                onChange={(e) => setPriceCents(Number(e.target.value))}
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {formatUSD(priceCents)}/mes
              </p>
            </div>
          </div>

          {/* Limits */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="edit-max-patients">Max. pacientes</Label>
              <Input
                id="edit-max-patients"
                type="number"
                min={-1}
                value={maxPatients}
                onChange={(e) => setMaxPatients(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-max-doctors">Max. doctores</Label>
              <Input
                id="edit-max-doctors"
                type="number"
                min={-1}
                value={maxDoctors}
                onChange={(e) => setMaxDoctors(Number(e.target.value))}
              />
            </div>
          </div>

          {/* Features JSON */}
          <div className="space-y-1.5">
            <Label htmlFor="edit-features">Características (JSON)</Label>
            <textarea
              id="edit-features"
              rows={8}
              value={featuresJson}
              onChange={(e) => handleFeaturesChange(e.target.value)}
              className={cn(
                "w-full rounded-md border bg-[hsl(var(--background))] px-3 py-2",
                "font-mono text-xs text-foreground shadow-sm",
                "resize-y focus:outline-none focus:ring-2 focus:ring-primary-600",
                "disabled:cursor-not-allowed disabled:opacity-50",
                jsonError
                  ? "border-red-500 dark:border-red-400"
                  : "border-[hsl(var(--border))]",
              )}
              spellCheck={false}
              aria-describedby={jsonError ? "edit-features-error" : undefined}
            />
            {jsonError && (
              <p
                id="edit-features-error"
                className="text-xs text-red-600 dark:text-red-400"
              >
                {jsonError}
              </p>
            )}
          </div>

          {/* Active toggle */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="edit-is-active"
              checked={isActive}
              onCheckedChange={(checked) => setIsActive(checked === true)}
            />
            <Label htmlFor="edit-is-active" className="cursor-pointer">
              Plan activo
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updatePlan.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            disabled={updatePlan.isPending || !!jsonError}
          >
            {updatePlan.isPending ? "Guardando..." : "Guardar cambios"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Plan Card ─────────────────────────────────────────────────────────────────

interface PlanCardProps {
  plan: PlanResponse;
  onEdit: (plan: PlanResponse) => void;
  onHistory: (plan: PlanResponse) => void;
}

function PlanCard({ plan, onEdit, onHistory }: PlanCardProps) {
  // Collect truthy feature keys for display
  const enabledFeatures = Object.entries(plan.features)
    .filter(([, value]) => Boolean(value))
    .map(([key]) => key);

  const isPerDoctor = plan.pricing_model === "per_doctor";

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{plan.name}</CardTitle>
          <Badge variant={plan.is_active ? "success" : "secondary"}>
            {plan.is_active ? "Activo" : "Inactivo"}
          </Badge>
        </div>
        <CardDescription className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
          {plan.slug}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 flex-1">
        {/* Price */}
        <p className="text-2xl font-bold tabular-nums">
          {formatUSD(plan.price_cents)}
          <span className="text-sm font-normal text-[hsl(var(--muted-foreground))]">
            {" "}
            /mes
          </span>
        </p>

        {/* Pricing model */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-[hsl(var(--muted))] px-2.5 py-0.5 text-xs font-medium text-[hsl(var(--muted-foreground))]">
            {formatPricingModel(plan.pricing_model)}
          </span>
        </div>

        {/* Per-doctor pricing breakdown */}
        {isPerDoctor && (
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Incluye{" "}
            <span className="font-medium text-foreground">
              {plan.included_doctors}{" "}
              {plan.included_doctors === 1 ? "doctor" : "doctor(es)"}
            </span>
            ,{" "}
            <span className="font-medium text-foreground">
              {formatUSD(plan.additional_doctor_price_cents)}/doctor adicional
            </span>
          </p>
        )}

        {/* Limits */}
        <div className="space-y-1 text-sm text-[hsl(var(--muted-foreground))]">
          <p>
            Max. pacientes:{" "}
            <span className="font-medium text-foreground">
              {plan.max_patients === -1 ? "Ilimitado" : plan.max_patients.toLocaleString("es-CO")}
            </span>
          </p>
          <p>
            Max. doctores:{" "}
            <span className="font-medium text-foreground">
              {plan.max_doctors === -1 ? "Ilimitado" : plan.max_doctors}
            </span>
          </p>
        </div>

        {/* Features */}
        {enabledFeatures.length > 0 && (
          <div className="border-t border-[hsl(var(--border))] pt-3">
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
              Características
            </p>
            <ul className="space-y-1">
              {enabledFeatures.map((feature) => (
                <li
                  key={feature}
                  className="flex items-center gap-1.5 text-xs text-foreground"
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-primary-500 shrink-0"
                    aria-hidden="true"
                  />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Action buttons pinned to bottom */}
        <div className="mt-auto pt-3 flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onHistory(plan)}
          >
            Historial
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onEdit(plan)}
          >
            Editar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminPlansPage() {
  const { data: plans, isLoading, isError, refetch } = useAdminPlans();
  const [editingPlan, setEditingPlan] = React.useState<PlanResponse | null>(null);
  const [historyPlan, setHistoryPlan] = React.useState<PlanResponse | null>(null);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Planes</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Gestiona los planes de suscripción disponibles en la plataforma.
          </p>
        </div>
        <PlansLoadingSkeleton />
      </div>
    );
  }

  if (isError || !plans) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Planes</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar los planes. Verifica la conexión con la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Planes</h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Gestiona los planes de suscripción disponibles en la plataforma.{" "}
          <span className="font-medium text-foreground">
            {plans.length} {plans.length === 1 ? "plan" : "planes"} configurados.
          </span>
        </p>
      </div>

      {/* Plan cards */}
      {plans.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-[hsl(var(--muted-foreground))]">
            No hay planes configurados.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              onEdit={setEditingPlan}
              onHistory={setHistoryPlan}
            />
          ))}
        </div>
      )}

      {/* Edit dialog — rendered once, driven by editingPlan state */}
      {editingPlan && (
        <EditPlanDialog
          plan={editingPlan}
          open={editingPlan !== null}
          onOpenChange={(open) => {
            if (!open) setEditingPlan(null);
          }}
        />
      )}

      {/* History modal — rendered once, driven by historyPlan state */}
      {historyPlan && (
        <PlanHistoryModal
          plan={historyPlan}
          open={historyPlan !== null}
          onOpenChange={(open) => {
            if (!open) setHistoryPlan(null);
          }}
        />
      )}
    </div>
  );
}
