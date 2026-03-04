"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ChevronLeft,
  FlaskConical,
  User,
  Building2,
  CalendarDays,
  Banknote,
  ArrowRight,
  CheckCircle2,
  Clock,
  Circle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LabOrderStatusBadge } from "@/components/lab-orders/lab-order-status-badge";
import {
  useLabOrder,
  useAdvanceLabOrder,
  useDentalLabs,
} from "@/lib/hooks/use-lab-orders";
import { formatDate, formatDateTime, formatCurrency, cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const ORDER_TYPE_LABELS: Record<string, string> = {
  corona: "Corona",
  puente: "Puente",
  protesis: "Prótesis",
  abutment_implante: "Abutment implante",
  retenedor: "Retenedor",
  otro: "Otro",
};

const STATUS_TRANSITIONS: Record<string, { next: string; label: string }> = {
  pending: { next: "sent_to_lab", label: "Marcar como enviada al lab" },
  sent_to_lab: { next: "in_progress", label: "Marcar como en proceso" },
  in_progress: { next: "ready", label: "Marcar como lista" },
  ready: { next: "delivered", label: "Marcar como entregada" },
};

// ─── Timeline step ────────────────────────────────────────────────────────────

function TimelineStep({
  label,
  timestamp,
  done,
  isLast,
}: {
  label: string;
  timestamp: string | null;
  done: boolean;
  isLast?: boolean;
}) {
  return (
    <div className="flex gap-3">
      {/* Dot + connector */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "h-8 w-8 rounded-full flex items-center justify-center border-2 shrink-0 z-10",
            done
              ? "bg-primary-600 border-primary-600 text-white"
              : "bg-[hsl(var(--background))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]",
          )}
        >
          {done ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <Circle className="h-4 w-4" />
          )}
        </div>
        {!isLast && (
          <div
            className={cn(
              "w-0.5 flex-1 mt-1",
              done
                ? "bg-primary-600"
                : "bg-[hsl(var(--border))]",
            )}
          />
        )}
      </div>

      {/* Content */}
      <div className="pb-6">
        <p
          className={cn(
            "text-sm font-medium leading-none mt-1.5",
            done ? "text-foreground" : "text-[hsl(var(--muted-foreground))]",
          )}
        >
          {label}
        </p>
        {timestamp && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
            {formatDateTime(timestamp)}
          </p>
        )}
        {!timestamp && done && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
            —
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function OrderDetailSkeleton() {
  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="space-y-2">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-7 w-48" />
      </div>
      <Skeleton className="h-6 w-24" />
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-32 rounded-xl" />
      <Skeleton className="h-40 rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LabOrderDetailPage() {
  const params = useParams<{ id: string }>();
  const orderId = params.id;

  const { data: order, isLoading } = useLabOrder(orderId);
  const { data: labs } = useDentalLabs();
  const advanceOrder = useAdvanceLabOrder(orderId);

  const labMap = React.useMemo(
    () =>
      (labs ?? []).reduce<Record<string, string>>((acc, lab) => {
        acc[lab.id] = lab.name;
        return acc;
      }, {}),
    [labs],
  );

  if (isLoading || !order) {
    return <OrderDetailSkeleton />;
  }

  const orderTypeLabel =
    ORDER_TYPE_LABELS[order.order_type] ?? order.order_type;
  const labName = order.lab_id ? labMap[order.lab_id] : null;
  const transition = STATUS_TRANSITIONS[order.status];

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const isOverdue =
    order.due_date != null &&
    !["delivered", "cancelled"].includes(order.status) &&
    new Date(order.due_date) < today;

  // Timeline steps
  const timelineSteps = [
    {
      label: "Orden creada",
      timestamp: order.created_at,
      done: true,
    },
    {
      label: "Enviada al laboratorio",
      timestamp: order.sent_at,
      done: order.sent_at != null,
    },
    {
      label: "En proceso",
      timestamp: null,
      done: ["in_progress", "ready", "delivered"].includes(order.status),
    },
    {
      label: "Lista para retirar",
      timestamp: order.ready_at,
      done: order.ready_at != null,
    },
    {
      label: "Entregada al paciente",
      timestamp: order.delivered_at,
      done: order.delivered_at != null,
      isLast: true,
    },
  ];

  // Try to display specifications
  let specificationsDisplay: React.ReactNode = null;
  if (order.specifications) {
    // specifications can be a JSONB object or a plain string
    if (typeof order.specifications === "object") {
      specificationsDisplay = (
        <pre className="text-xs font-mono bg-[hsl(var(--muted))] rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap">
          {JSON.stringify(order.specifications, null, 2)}
        </pre>
      );
    } else {
      try {
        const parsed = JSON.parse(order.specifications);
        specificationsDisplay = (
          <pre className="text-xs font-mono bg-[hsl(var(--muted))] rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        );
      } catch {
        specificationsDisplay = (
          <p className="text-sm text-foreground whitespace-pre-wrap">
            {order.specifications}
          </p>
        );
      }
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Back link + header */}
      <div className="space-y-2">
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href="/lab-orders">
            <ChevronLeft className="mr-1 h-4 w-4" />
            Volver a órdenes
          </Link>
        </Button>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-primary-600 shrink-0" />
            <h1 className="text-lg font-semibold text-foreground">
              {orderTypeLabel}
            </h1>
          </div>
        </div>
      </div>

      {/* Status badge (large) */}
      <LabOrderStatusBadge status={order.status} className="text-sm px-3 py-1" />

      {/* Info cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Patient */}
        <Card>
          <CardContent className="flex items-start gap-3 pt-4 pb-4">
            <User className="h-4 w-4 text-[hsl(var(--muted-foreground))] mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Paciente</p>
              <p className="text-sm font-medium font-mono truncate text-foreground">
                {order.patient_id}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Lab */}
        <Card>
          <CardContent className="flex items-start gap-3 pt-4 pb-4">
            <Building2 className="h-4 w-4 text-[hsl(var(--muted-foreground))] mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Laboratorio</p>
              <p className="text-sm font-medium text-foreground truncate">
                {labName ?? "Sin asignar"}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Due date */}
        <Card className={isOverdue ? "border-red-300 dark:border-red-800" : ""}>
          <CardContent className="flex items-start gap-3 pt-4 pb-4">
            <CalendarDays
              className={cn(
                "h-4 w-4 mt-0.5 shrink-0",
                isOverdue
                  ? "text-red-600 dark:text-red-400"
                  : "text-[hsl(var(--muted-foreground))]",
              )}
            />
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Fecha de entrega
              </p>
              <p
                className={cn(
                  "text-sm font-medium",
                  isOverdue
                    ? "text-red-600 dark:text-red-400"
                    : "text-foreground",
                )}
              >
                {order.due_date ? formatDate(order.due_date) : "Sin fecha"}
                {isOverdue && (
                  <span className="ml-1 text-xs font-normal">(Vencida)</span>
                )}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Cost */}
        <Card>
          <CardContent className="flex items-start gap-3 pt-4 pb-4">
            <Banknote className="h-4 w-4 text-[hsl(var(--muted-foreground))] mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Costo</p>
              <p className="text-sm font-medium text-foreground">
                {order.cost_cents != null
                  ? formatCurrency(order.cost_cents, "COP")
                  : "No especificado"}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Specifications */}
      {order.specifications && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">
              Especificaciones
            </CardTitle>
          </CardHeader>
          <CardContent>{specificationsDisplay}</CardContent>
        </Card>
      )}

      {/* Status timeline */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
            <CardTitle className="text-sm font-semibold">
              Línea de tiempo
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="ml-2">
            {timelineSteps.map((step, idx) => (
              <TimelineStep
                key={step.label}
                label={step.label}
                timestamp={step.timestamp}
                done={step.done}
                isLast={idx === timelineSteps.length - 1}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Notes */}
      {order.notes && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">
              Notas internas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground whitespace-pre-wrap">
              {order.notes}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Advance status action */}
      {transition && (
        <div className="flex items-center gap-3 pt-2">
          <Button
            onClick={() => advanceOrder.mutate()}
            disabled={advanceOrder.isPending}
            className="gap-2"
          >
            {advanceOrder.isPending ? (
              "Actualizando..."
            ) : (
              <>
                {transition.label}
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Próximo estado:{" "}
            <span className="font-medium">
              <LabOrderStatusBadge status={transition.next} />
            </span>
          </p>
        </div>
      )}

      {/* Cancelled */}
      {order.status === "cancelled" && (
        <p className="text-sm text-[hsl(var(--muted-foreground))] italic">
          Esta orden fue cancelada y no puede avanzar de estado.
        </p>
      )}
    </div>
  );
}
