"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MembershipPlanCard } from "@/components/membership-plan-card";
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
import { CreditCard, CheckCircle2, XCircle } from "lucide-react";
import { formatCurrency, formatDate } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ActiveMembership {
  id: string;
  plan_id: string;
  plan_name: string;
  monthly_price_cents: number;
  discount_percentage: number;
  benefits: Record<string, unknown> | null;
  start_date: string;
  next_billing_date: string;
  status: "active" | "cancelled" | "past_due";
}

interface MembershipPlan {
  id: string;
  name: string;
  description: string | null;
  monthly_price_cents: number;
  discount_percentage: number;
  benefits: Record<string, unknown> | null;
  is_active: boolean;
}

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  active: "Activa",
  cancelled: "Cancelada",
  past_due: "Vencida",
};

const STATUS_VARIANTS: Record<string, "success" | "secondary" | "destructive"> = {
  active: "success",
  cancelled: "secondary",
  past_due: "destructive",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientMembershipPage() {
  const params = useParams<{ id: string }>();
  const patientId = params?.id ?? "";
  const queryClient = useQueryClient();

  const { data: membership, isLoading: isLoadingMembership } = useQuery({
    queryKey: ["patients", patientId, "membership"],
    queryFn: () =>
      apiGet<ActiveMembership | null>(`/patients/${patientId}/membership`).catch(() => null),
    staleTime: 30_000,
  });

  const { data: plans, isLoading: isLoadingPlans } = useQuery({
    queryKey: ["memberships", "plans", "active"],
    queryFn: () => apiGet<MembershipPlan[]>("/memberships/plans?active=true"),
    staleTime: 60_000,
    enabled: !membership || membership.status !== "active",
  });

  const { mutate: subscribe, isPending: isSubscribing } = useMutation({
    mutationFn: (planId: string) =>
      apiPost(`/patients/${patientId}/membership`, { plan_id: planId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients", patientId, "membership"] });
      setSelectedPlanId(null);
    },
  });

  const { mutate: cancelMembership, isPending: isCancelling } = useMutation({
    mutationFn: () => apiPost(`/patients/${patientId}/membership/cancel`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients", patientId, "membership"] });
      setCancelDialogOpen(false);
    },
  });

  const [selectedPlanId, setSelectedPlanId] = React.useState<string | null>(null);
  const [cancelDialogOpen, setCancelDialogOpen] = React.useState(false);

  const isLoading = isLoadingMembership || isLoadingPlans;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-40 rounded-xl" />
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-52 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Membresía del paciente</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Administra la membresía activa o suscribe al paciente a un plan.
        </p>
      </div>

      {/* Active membership */}
      {membership && membership.status === "active" ? (
        <Card className="border-primary-200 dark:border-primary-800">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                Membresía activa
              </CardTitle>
              <Badge variant={STATUS_VARIANTS[membership.status]}>
                {STATUS_LABELS[membership.status]}
              </Badge>
            </div>
            <CardDescription>{membership.plan_name}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Precio mensual</p>
                <p className="font-semibold tabular-nums">
                  {formatCurrency(membership.monthly_price_cents)}
                </p>
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Descuento</p>
                <p className="font-semibold text-green-600">
                  {membership.discount_percentage}%
                </p>
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Desde</p>
                <p className="font-medium">{formatDate(membership.start_date)}</p>
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Próxima facturación
                </p>
                <p className="font-medium">{formatDate(membership.next_billing_date)}</p>
              </div>
            </div>

            {membership.benefits && Object.keys(membership.benefits).length > 0 && (
              <div>
                <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-2">
                  Beneficios incluidos
                </p>
                <ul className="space-y-1">
                  {Object.keys(membership.benefits).map((key) => (
                    <li key={key} className="flex items-center gap-2 text-sm">
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
                      {key}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="pt-2 border-t border-[hsl(var(--border))]">
              <Button
                variant="outline"
                size="sm"
                className="text-destructive border-destructive/30 hover:bg-destructive/10"
                onClick={() => setCancelDialogOpen(true)}
              >
                <XCircle className="mr-2 h-3.5 w-3.5" />
                Cancelar membresía
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        /* Plan selector */
        <>
          {membership && membership.status !== "active" && (
            <Card className="border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/10">
              <CardContent className="py-4 flex items-center gap-3">
                <XCircle className="h-4 w-4 text-orange-500 shrink-0" />
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  La membresía anterior está{" "}
                  <span className="font-medium text-foreground">
                    {STATUS_LABELS[membership.status]?.toLowerCase()}
                  </span>
                  . Suscribe al paciente a un nuevo plan.
                </p>
              </CardContent>
            </Card>
          )}

          <div>
            <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-primary-600" />
              Seleccionar plan
            </h2>

            {!plans || plans.length === 0 ? (
              <Card>
                <CardContent className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
                  No hay planes de membresía disponibles. Configúralos en{" "}
                  <strong>Configuración → Membresías</strong>.
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {plans.map((plan) => (
                  <MembershipPlanCard
                    key={plan.id}
                    plan={plan}
                    selected={selectedPlanId === plan.id}
                    actionLabel="Suscribir"
                    onAction={() => setSelectedPlanId(plan.id)}
                  />
                ))}
              </div>
            )}
          </div>

          {selectedPlanId && (
            <div className="flex items-center gap-3 pt-2">
              <Button
                onClick={() => subscribe(selectedPlanId)}
                disabled={isSubscribing}
              >
                {isSubscribing ? "Suscribiendo..." : "Confirmar suscripción"}
              </Button>
              <Button
                variant="outline"
                onClick={() => setSelectedPlanId(null)}
                disabled={isSubscribing}
              >
                Cancelar
              </Button>
            </div>
          )}
        </>
      )}

      {/* Cancel confirmation */}
      <AlertDialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar membresía</AlertDialogTitle>
            <AlertDialogDescription>
              ¿Estás seguro de que deseas cancelar la membresía del paciente? Los beneficios
              activos se mantendrán hasta el final del período facturado.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isCancelling}>Atrás</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => cancelMembership()}
              disabled={isCancelling}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isCancelling ? "Cancelando..." : "Sí, cancelar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
