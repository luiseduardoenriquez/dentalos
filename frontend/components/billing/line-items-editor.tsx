"use client";

import * as React from "react";
import {
  useFieldArray,
  useFormContext,
  type UseFormReturn,
} from "react-hook-form";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { formatCurrency } from "@/lib/utils";
import { BillableItemsPicker } from "@/components/billing/billable-items-picker";
import { BillableOrthoItemsPicker } from "@/components/billing/billable-ortho-items-picker";
import type { BillableItem, BillableOrthoItem } from "@/lib/hooks/use-invoices";

interface LineItemsEditorProps {
  patientId?: string;
  disabled?: boolean;
}

export function LineItemsEditor({ patientId, disabled = false }: LineItemsEditorProps) {
  const {
    register,
    watch,
    control,
    formState: { errors },
  } = useFormContext();

  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });

  function handleAddItem() {
    append({
      description: "",
      service_id: null,
      cups_code: "",
      quantity: "1",
      unit_price_display: "",
      discount_display: "0",
      tooth_number: "",
    });
  }

  function handleLoadBillableItems(items: BillableItem[]) {
    for (const item of items) {
      const cost = item.actual_cost || item.estimated_cost;
      append({
        description: item.cups_description,
        service_id: null,
        cups_code: item.cups_code || "",
        quantity: "1",
        unit_price_display: String(cost / 100),
        discount_display: "0",
        tooth_number: item.tooth_number ? String(item.tooth_number) : "",
        treatment_plan_item_id: item.treatment_plan_item_id || null,
      });
    }
  }

  function handleLoadOrthoItems(items: BillableOrthoItem[]) {
    for (const item of items) {
      append({
        description: item.description,
        service_id: null,
        cups_code: null,
        quantity: "1",
        unit_price_display: String(item.amount / 100),
        discount_display: "0",
        tooth_number: "",
        ortho_case_id: item.ortho_case_id || null,
        ortho_visit_id: item.ortho_visit_id || null,
      });
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <p className="text-sm font-semibold text-foreground">Ítems</p>
        <div className="flex items-center gap-2 flex-wrap">
          {patientId && (
            <BillableItemsPicker
              patientId={patientId}
              onSelect={handleLoadBillableItems}
              disabled={disabled}
            />
          )}
          {patientId && (
            <BillableOrthoItemsPicker
              patientId={patientId}
              onSelect={handleLoadOrthoItems}
              disabled={disabled}
            />
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddItem}
            disabled={disabled}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Agregar ítem
          </Button>
        </div>
      </div>

      {fields.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center rounded-lg border border-dashed border-[hsl(var(--border))]">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            No hay ítems. Agrega el primero.
          </p>
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {patientId && (
              <BillableItemsPicker
                patientId={patientId}
                onSelect={handleLoadBillableItems}
                disabled={disabled}
              />
            )}
            {patientId && (
              <BillableOrthoItemsPicker
                patientId={patientId}
                onSelect={handleLoadOrthoItems}
                disabled={disabled}
              />
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddItem}
              disabled={disabled}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Agregar ítem
            </Button>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[200px]">Descripción</TableHead>
                <TableHead className="w-[80px]">Cant.</TableHead>
                <TableHead className="w-[140px]">Precio unit. (COP)</TableHead>
                <TableHead className="w-[120px]">Descuento (COP)</TableHead>
                <TableHead className="w-[140px] text-right">Subtotal</TableHead>
                <TableHead className="w-[50px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {fields.map((field, index) => {
                const qty = parseInt(watch(`items.${index}.quantity`) || "0", 10) || 0;
                const price = parseInt(watch(`items.${index}.unit_price_display`) || "0", 10) || 0;
                const disc = parseInt(watch(`items.${index}.discount_display`) || "0", 10) || 0;
                const lineTotal = Math.max(0, qty * price * 100 - disc * 100);

                return (
                  <TableRow key={field.id}>
                    <TableCell>
                      <Input
                        placeholder="Descripción del servicio"
                        className="h-8 text-sm"
                        {...register(`items.${index}.description`)}
                        disabled={disabled}
                      />
                      {(errors.items as any)?.[index]?.description && (
                        <p className="text-[10px] text-destructive mt-0.5">
                          {(errors.items as Record<string, any>)?.[index]?.description?.message}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={1}
                        className="h-8 text-sm tabular-nums"
                        {...register(`items.${index}.quantity`)}
                        disabled={disabled}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="text"
                        inputMode="numeric"
                        placeholder="150000"
                        className="h-8 text-sm tabular-nums"
                        {...register(`items.${index}.unit_price_display`)}
                        disabled={disabled}
                      />
                      {(errors.items as any)?.[index]?.unit_price_display && (
                        <p className="text-[10px] text-destructive mt-0.5">
                          {(errors.items as Record<string, any>)?.[index]?.unit_price_display?.message}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <Input
                        type="text"
                        inputMode="numeric"
                        placeholder="0"
                        className="h-8 text-sm tabular-nums"
                        {...register(`items.${index}.discount_display`)}
                        disabled={disabled}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="text-sm font-medium tabular-nums">
                        {formatCurrency(lineTotal, "COP")}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                        onClick={() => remove(index)}
                        disabled={disabled}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        <span className="sr-only">Eliminar ítem</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Items-level error */}
      {errors.items && !Array.isArray(errors.items) && (
        <p className="text-xs text-destructive mt-2">
          {(errors.items as { message?: string }).message}
        </p>
      )}
    </div>
  );
}
