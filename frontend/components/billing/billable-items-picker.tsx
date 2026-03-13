"use client";

import * as React from "react";
import { ClipboardList, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { formatCurrency } from "@/lib/utils";
import {
  useBillableItems,
  type BillableItem,
} from "@/lib/hooks/use-invoices";

interface BillableItemsPickerProps {
  patientId: string;
  onSelect: (items: BillableItem[]) => void;
  disabled?: boolean;
}

export function BillableItemsPicker({
  patientId,
  onSelect,
  disabled = false,
}: BillableItemsPickerProps) {
  const { data, isLoading } = useBillableItems(patientId);
  const [open, setOpen] = React.useState(false);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());

  const items = data?.items ?? [];

  function toggleItem(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((i) => i.treatment_plan_item_id)));
    }
  }

  function handleConfirm() {
    const chosen = items.filter((i) =>
      selected.has(i.treatment_plan_item_id),
    );
    onSelect(chosen);
    setOpen(false);
    setSelected(new Set());
  }

  if (isLoading) {
    return (
      <Button type="button" variant="outline" size="sm" disabled>
        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        Cargando tratamientos...
      </Button>
    );
  }

  if (items.length === 0) {
    return null;
  }

  if (!open) {
    return (
      <Button
        type="button"
        variant="default"
        size="sm"
        onClick={() => {
          setOpen(true);
          setSelected(new Set(items.map((i) => i.treatment_plan_item_id)));
        }}
        disabled={disabled}
      >
        <ClipboardList className="mr-1.5 h-3.5 w-3.5" />
        Cargar desde tratamiento ({items.length})
      </Button>
    );
  }

  const totalSelected = items
    .filter((i) => selected.has(i.treatment_plan_item_id))
    .reduce((sum, i) => sum + (i.actual_cost || i.estimated_cost), 0);

  return (
    <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-foreground">
          Conceptos del plan de tratamiento
        </p>
        <button
          type="button"
          onClick={toggleAll}
          className="text-xs text-primary hover:underline"
        >
          {selected.size === items.length ? "Deseleccionar todo" : "Seleccionar todo"}
        </button>
      </div>

      <div className="space-y-2">
        {items.map((item) => {
          const cost = item.actual_cost || item.estimated_cost;
          const isSelected = selected.has(item.treatment_plan_item_id);

          return (
            <label
              key={item.treatment_plan_item_id}
              className={`flex items-center gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                isSelected
                  ? "border-primary bg-primary/10"
                  : "border-[hsl(var(--border))] hover:bg-[hsl(var(--muted)/0.3)]"
              }`}
            >
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => toggleItem(item.treatment_plan_item_id)}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {item.cups_description}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  {item.cups_code && (
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">
                      CUPS {item.cups_code}
                    </span>
                  )}
                  {item.tooth_number && (
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">
                      Diente {item.tooth_number}
                    </span>
                  )}
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                    item.status === "completed"
                      ? "bg-green-500/10 text-green-500"
                      : "bg-yellow-500/10 text-yellow-500"
                  }`}>
                    {item.status === "completed" ? "Realizado" : "Agendado"}
                  </span>
                </div>
              </div>
              <span className="text-sm font-semibold tabular-nums text-foreground whitespace-nowrap">
                {formatCurrency(cost, "COP")}
              </span>
            </label>
          );
        })}
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))]">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {selected.size} de {items.length} seleccionados —{" "}
          <span className="font-semibold text-foreground">
            {formatCurrency(totalSelected, "COP")}
          </span>
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setOpen(false);
              setSelected(new Set());
            }}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={handleConfirm}
            disabled={selected.size === 0}
          >
            <Check className="mr-1.5 h-3.5 w-3.5" />
            Agregar {selected.size} ítems
          </Button>
        </div>
      </div>
    </div>
  );
}
