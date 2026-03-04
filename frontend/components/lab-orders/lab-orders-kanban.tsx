"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { LabOrderCard } from "@/components/lab-orders/lab-order-card";
import type { LabOrderResponse, DentalLabResponse } from "@/lib/hooks/use-lab-orders";

// ─── Constants ────────────────────────────────────────────────────────────────

const KANBAN_COLUMNS: Array<{
  status: string;
  label: string;
  headerClass: string;
}> = [
  {
    status: "pending",
    label: "Pendiente",
    headerClass: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  {
    status: "sent_to_lab",
    label: "Enviada al lab",
    headerClass: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  },
  {
    status: "in_progress",
    label: "En proceso",
    headerClass: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  },
  {
    status: "ready",
    label: "Lista",
    headerClass: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  },
  {
    status: "delivered",
    label: "Entregada",
    headerClass: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface LabOrdersKanbanProps {
  orders: LabOrderResponse[];
  labs?: DentalLabResponse[];
  onOrderClick: (orderId: string) => void;
}

// ─── Column ───────────────────────────────────────────────────────────────────

function KanbanColumn({
  label,
  headerClass,
  orders,
  labs,
  onOrderClick,
}: {
  label: string;
  headerClass: string;
  orders: LabOrderResponse[];
  labs?: DentalLabResponse[];
  onOrderClick: (orderId: string) => void;
}) {
  const labMap = React.useMemo(() => {
    if (!labs) return {} as Record<string, string>;
    return labs.reduce<Record<string, string>>((acc, lab) => {
      acc[lab.id] = lab.name;
      return acc;
    }, {});
  }, [labs]);

  return (
    <div className="flex flex-col min-w-[220px] flex-1 max-w-[300px]">
      {/* Column header */}
      <div
        className={cn(
          "flex items-center justify-between px-3 py-2 rounded-t-lg mb-2",
          headerClass,
        )}
      >
        <span className="text-xs font-semibold">{label}</span>
        <Badge
          variant="secondary"
          className={cn(
            "text-xs ml-1 min-w-[1.25rem] text-center",
            headerClass,
            "border border-current/20",
          )}
        >
          {orders.length}
        </Badge>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[120px]">
        {orders.length === 0 ? (
          <div className="text-xs text-[hsl(var(--muted-foreground))] text-center py-6 border border-dashed border-[hsl(var(--border))] rounded-lg">
            Sin órdenes
          </div>
        ) : (
          orders.map((order) => (
            <LabOrderCard
              key={order.id}
              order={order}
              labName={order.lab_id ? labMap[order.lab_id] : undefined}
              onClick={() => onOrderClick(order.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function LabOrdersKanban({ orders, labs, onOrderClick }: LabOrdersKanbanProps) {
  const ordersByStatus = React.useMemo(() => {
    return KANBAN_COLUMNS.reduce<Record<string, LabOrderResponse[]>>(
      (acc, col) => {
        acc[col.status] = orders.filter((o) => o.status === col.status);
        return acc;
      },
      {},
    );
  }, [orders]);

  return (
    <div className="flex gap-3 overflow-x-auto pb-4">
      {KANBAN_COLUMNS.map((col) => (
        <KanbanColumn
          key={col.status}
          label={col.label}
          headerClass={col.headerClass}
          orders={ordersByStatus[col.status] ?? []}
          labs={labs}
          onOrderClick={onOrderClick}
        />
      ))}
    </div>
  );
}
