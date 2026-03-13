"use client";

import * as React from "react";
import { Stethoscope, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { formatCurrency } from "@/lib/utils";
import {
  useBillableOrthoItems,
  type BillableOrthoItem,
} from "@/lib/hooks/use-invoices";

interface BillableOrthoItemsPickerProps {
  patientId: string;
  onSelect: (items: BillableOrthoItem[]) => void;
  disabled?: boolean;
}

export function BillableOrthoItemsPicker({
  patientId,
  onSelect,
  disabled = false,
}: BillableOrthoItemsPickerProps) {
  const { data, isLoading } = useBillableOrthoItems(patientId);
  const [open, setOpen] = React.useState(false);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());

  const items = data?.items ?? [];

  // Unique key per item: visit_id for controls, case_id for initial payments
  function itemKey(item: BillableOrthoItem): string {
    return item.ortho_visit_id ?? `initial_${item.ortho_case_id}`;
  }

  function toggleItem(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map(itemKey)));
    }
  }

  function handleConfirm() {
    const chosen = items.filter((i) => selected.has(itemKey(i)));
    onSelect(chosen);
    setOpen(false);
    setSelected(new Set());
  }

  if (isLoading) {
    return (
      <Button type="button" variant="outline" size="sm" disabled>
        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        Cargando ortodoncia...
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
          setSelected(new Set(items.map(itemKey)));
        }}
        disabled={disabled}
        className="bg-violet-600 hover:bg-violet-700"
      >
        <Stethoscope className="mr-1.5 h-3.5 w-3.5" />
        Cargar desde ortodoncia ({items.length})
      </Button>
    );
  }

  const totalSelected = items
    .filter((i) => selected.has(itemKey(i)))
    .reduce((sum, i) => sum + i.amount, 0);

  return (
    <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-foreground">
          Conceptos de ortodoncia
        </p>
        <button
          type="button"
          onClick={toggleAll}
          className="text-xs text-violet-500 hover:underline"
        >
          {selected.size === items.length ? "Deseleccionar todo" : "Seleccionar todo"}
        </button>
      </div>

      <div className="space-y-2">
        {items.map((item) => {
          const key = itemKey(item);
          const isSelected = selected.has(key);

          return (
            <label
              key={key}
              className={`flex items-center gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                isSelected
                  ? "border-violet-500 bg-violet-500/10"
                  : "border-[hsl(var(--border))] hover:bg-[hsl(var(--muted)/0.3)]"
              }`}
            >
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => toggleItem(key)}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {item.description}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    {item.case_number}
                  </span>
                  {item.visit_date && (
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">
                      {new Date(item.visit_date + "T12:00:00").toLocaleDateString("es-CO")}
                    </span>
                  )}
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                    item.type === "initial_payment"
                      ? "bg-violet-500/10 text-violet-500"
                      : "bg-cyan-500/10 text-cyan-500"
                  }`}>
                    {item.type === "initial_payment" ? "Cuota inicial" : `Control #${item.visit_number}`}
                  </span>
                </div>
              </div>
              <span className="text-sm font-semibold tabular-nums text-foreground whitespace-nowrap">
                {formatCurrency(item.amount, "COP")}
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
            className="bg-violet-600 hover:bg-violet-700"
          >
            <Check className="mr-1.5 h-3.5 w-3.5" />
            Agregar {selected.size} items
          </Button>
        </div>
      </div>
    </div>
  );
}
