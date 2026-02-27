"use client";

import * as React from "react";
import Link from "next/link";
import { RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useInventoryAlerts, type InventoryAlertItem } from "@/lib/hooks/use-inventory";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  material: "Material",
  instrument: "Instrumento",
  implant: "Implante",
  medication: "Medicamento",
};

// ─── Alert Item Row ───────────────────────────────────────────────────────────

function AlertItemRow({
  item,
  showExpiry,
}: {
  item: InventoryAlertItem;
  showExpiry: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[hsl(var(--border))] last:border-0 gap-4">
      <div className="flex flex-col gap-0.5 min-w-0">
        <Link
          href={`/inventory/${item.id}`}
          className="text-sm font-medium text-foreground hover:text-primary-600 transition-colors truncate"
        >
          {item.name}
        </Link>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {CATEGORY_LABELS[item.category] ?? item.category}
          </Badge>
          {showExpiry && item.expiry_date && (
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              Vence:{" "}
              <span className="font-medium">
                {new Date(item.expiry_date).toLocaleDateString("es-CO")}
              </span>
            </span>
          )}
        </div>
      </div>
      <div className="flex flex-col items-end gap-0.5 shrink-0">
        <span className="text-sm font-semibold tabular-nums text-foreground">
          {item.quantity}
        </span>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          Mín: {item.minimum_stock}
        </span>
      </div>
    </div>
  );
}

// ─── Alert Section ────────────────────────────────────────────────────────────

function AlertSection({
  title,
  items,
  showExpiry,
  headerColorClass,
  emptyMessage,
}: {
  title: string;
  items: InventoryAlertItem[];
  showExpiry: boolean;
  headerColorClass: string;
  emptyMessage: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle
          className={cn(
            "flex items-center gap-2 text-base font-semibold",
            headerColorClass,
          )}
        >
          {items.length > 0 ? (
            <AlertTriangle className="h-4 w-4 shrink-0" />
          ) : (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          )}
          {title}
          {items.length > 0 && (
            <span
              className={cn(
                "ml-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-xs font-bold text-white",
                items.length > 0 ? "bg-current opacity-90" : "",
              )}
            >
              {items.length}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="py-4 text-center text-sm text-[hsl(var(--muted-foreground))]">
            {emptyMessage}
          </p>
        ) : (
          <div>
            {items.map((item) => (
              <AlertItemRow key={item.id} item={item} showExpiry={showExpiry} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InventoryAlertsPage() {
  const { data: alerts, isLoading } = useInventoryAlerts();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
      </div>
    );
  }

  const expired = alerts?.expired ?? [];
  const critical = alerts?.critical ?? [];
  const lowStock = alerts?.low_stock ?? [];

  const totalAlerts = expired.length + critical.length + lowStock.length;

  return (
    <div className="flex flex-col gap-6">
      {/* Summary */}
      {totalAlerts === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-[hsl(var(--muted-foreground))]">
          <CheckCircle2 className="h-12 w-12 text-green-500 opacity-70" />
          <p className="text-base font-medium text-foreground">
            Todo en orden
          </p>
          <p className="text-sm text-center">
            No hay artículos vencidos, por vencer ni con stock bajo.
          </p>
        </div>
      ) : (
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Se encontraron{" "}
          <span className="font-semibold text-foreground">{totalAlerts}</span>{" "}
          {totalAlerts === 1 ? "alerta" : "alertas"} en el inventario.
        </p>
      )}

      {/* Section 1: Expired — red */}
      <AlertSection
        title="Vencidos"
        items={expired}
        showExpiry
        headerColorClass="text-[#ef4444]"
        emptyMessage="Sin alertas"
      />

      {/* Section 2: Critical (within 30 days) — orange */}
      <AlertSection
        title="Por vencer (30 días)"
        items={critical}
        showExpiry
        headerColorClass="text-[#f97316]"
        emptyMessage="Sin alertas"
      />

      {/* Section 3: Low stock — yellow */}
      <AlertSection
        title="Stock bajo"
        items={lowStock}
        showExpiry={false}
        headerColorClass="text-[#eab308]"
        emptyMessage="Sin alertas"
      />
    </div>
  );
}
