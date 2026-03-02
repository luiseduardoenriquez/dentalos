"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  CreditCard,
  MoreHorizontal,
  Plus,
  Pencil,
  Archive,
  AlertCircle,
} from "lucide-react";
import { formatCurrency, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface MembershipPlan {
  id: string;
  name: string;
  description: string | null;
  price_monthly: number;
  discount_percentage: number;
  benefits: string[];
  is_active: boolean;
  member_count: number;
}

interface PlanFormState {
  name: string;
  description: string;
  price_monthly: string;
  discount_percentage: string;
  benefits: string;
}

const EMPTY_FORM: PlanFormState = {
  name: "",
  description: "",
  price_monthly: "",
  discount_percentage: "0",
  benefits: "",
};

// ─── Plan row ─────────────────────────────────────────────────────────────────

function PlanRow({
  plan,
  onEdit,
  onArchive,
}: {
  plan: MembershipPlan;
  onEdit: (plan: MembershipPlan) => void;
  onArchive: (id: string) => void;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-lg border p-4 gap-4",
        !plan.is_active && "opacity-60",
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm text-foreground">{plan.name}</span>
          {!plan.is_active && (
            <Badge variant="secondary" className="text-xs">
              Archivado
            </Badge>
          )}
          {plan.discount_percentage > 0 && (
            <Badge variant="outline" className="text-xs text-green-700 border-green-300">
              -{plan.discount_percentage}% descuento
            </Badge>
          )}
        </div>
        {plan.description && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5 truncate">
            {plan.description}
          </p>
        )}
        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
          {plan.member_count} miembro{plan.member_count !== 1 ? "s" : ""}
        </p>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-sm font-semibold tabular-nums">
          {formatCurrency(plan.price_monthly)}
          <span className="text-xs font-normal text-[hsl(var(--muted-foreground))]">/mes</span>
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <MoreHorizontal className="h-4 w-4" />
              <span className="sr-only">Acciones</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(plan)}>
              <Pencil className="mr-2 h-3.5 w-3.5" />
              Editar
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-[hsl(var(--muted-foreground))]"
              onClick={() => onArchive(plan.id)}
            >
              <Archive className="mr-2 h-3.5 w-3.5" />
              {plan.is_active ? "Archivar" : "Reactivar"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MembershipPlansSettingsPage() {
  const queryClient = useQueryClient();

  const { data: plans, isLoading, isError } = useQuery({
    queryKey: ["settings", "membership-plans"],
    queryFn: () => apiGet<MembershipPlan[]>("/memberships/plans"),
    staleTime: 60_000,
  });

  const { mutate: savePlan, isPending: isSaving } = useMutation({
    mutationFn: (payload: { id?: string; data: Partial<MembershipPlan> }) =>
      payload.id
        ? apiPut(`/memberships/plans/${payload.id}`, payload.data)
        : apiPost("/memberships/plans", payload.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "membership-plans"] });
      setDialogOpen(false);
    },
  });

  const { mutate: toggleArchive } = useMutation({
    mutationFn: (id: string) => apiPut(`/memberships/plans/${id}/toggle-active`, {}),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["settings", "membership-plans"] }),
  });

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<MembershipPlan | null>(null);
  const [form, setForm] = React.useState<PlanFormState>(EMPTY_FORM);

  function openCreate() {
    setEditTarget(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  }

  function openEdit(plan: MembershipPlan) {
    setEditTarget(plan);
    setForm({
      name: plan.name,
      description: plan.description ?? "",
      price_monthly: String(plan.price_monthly / 100),
      discount_percentage: String(plan.discount_percentage),
      benefits: plan.benefits.join("\n"),
    });
    setDialogOpen(true);
  }

  function handleSave() {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      price_monthly: Math.round(parseFloat(form.price_monthly) * 100),
      discount_percentage: parseFloat(form.discount_percentage) || 0,
      benefits: form.benefits
        .split("\n")
        .map((b) => b.trim())
        .filter(Boolean),
    };
    savePlan({ id: editTarget?.id, data: payload });
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))] py-10 justify-center">
        <AlertCircle className="h-4 w-4 text-orange-500" />
        No se pudieron cargar los planes de membresía.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Planes de membresía</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Crea y administra los planes que puedes ofrecer a tus pacientes.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo plan
        </Button>
      </div>

      {/* Plan list */}
      {!plans || plans.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-14 gap-3">
            <CreditCard className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-50" />
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center">
              No hay planes de membresía creados.
              <br />
              Crea el primero para empezar a ofrecer beneficios a tus pacientes.
            </p>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Crear primer plan
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {plans.map((plan) => (
            <PlanRow
              key={plan.id}
              plan={plan}
              onEdit={openEdit}
              onArchive={(id) => toggleArchive(id)}
            />
          ))}
        </div>
      )}

      {/* Create / Edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editTarget ? "Editar plan" : "Nuevo plan de membresía"}
            </DialogTitle>
            <DialogDescription>
              Define el nombre, precio y beneficios del plan.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <Label htmlFor="plan-name">Nombre *</Label>
              <Input
                id="plan-name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Ej: Plan Familiar"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="plan-desc">Descripción</Label>
              <Input
                id="plan-desc"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Descripción corta del plan"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label htmlFor="plan-price">Precio mensual (COP) *</Label>
                <Input
                  id="plan-price"
                  type="number"
                  min={0}
                  value={form.price_monthly}
                  onChange={(e) => setForm((f) => ({ ...f, price_monthly: e.target.value }))}
                  placeholder="0"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="plan-discount">Descuento (%)</Label>
                <Input
                  id="plan-discount"
                  type="number"
                  min={0}
                  max={100}
                  value={form.discount_percentage}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, discount_percentage: e.target.value }))
                  }
                  placeholder="0"
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label htmlFor="plan-benefits">Beneficios (uno por línea)</Label>
              <textarea
                id="plan-benefits"
                rows={4}
                value={form.benefits}
                onChange={(e) => setForm((f) => ({ ...f, benefits: e.target.value }))}
                placeholder={"Limpieza dental gratis\nConsulta de valoración incluida"}
                className="flex w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm placeholder:text-[hsl(var(--muted-foreground))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 resize-none"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={isSaving}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={isSaving || !form.name.trim()}>
              {isSaving ? "Guardando..." : editTarget ? "Guardar cambios" : "Crear plan"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
