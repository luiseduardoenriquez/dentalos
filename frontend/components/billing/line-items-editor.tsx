"use client";

import * as React from "react";
import {
  useFieldArray,
  useFormContext,
  type UseFormReturn,
} from "react-hook-form";
import { Plus, Trash2, Search } from "lucide-react";
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
import {
  useServiceCatalog,
  type ServiceCatalogItem,
} from "@/lib/hooks/use-service-catalog";

// ─── Service Autocomplete Input ─────────────────────────────────────────────

interface ServiceAutocompleteProps {
  index: number;
  disabled?: boolean;
}

function ServiceAutocomplete({ index, disabled }: ServiceAutocompleteProps) {
  const { register, setValue, watch } = useFormContext();
  const [searchTerm, setSearchTerm] = React.useState("");
  const [isOpen, setIsOpen] = React.useState(false);
  const [highlightedIndex, setHighlightedIndex] = React.useState(-1);

  const description = watch(`items.${index}.description`) || "";

  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const { data } = useServiceCatalog(debouncedSearch, isOpen);
  const results = data?.items ?? [];

  function handleSelect(item: ServiceCatalogItem) {
    setValue(`items.${index}.description`, item.name, { shouldValidate: true });
    setValue(`items.${index}.cups_code`, item.cups_code || "", { shouldValidate: true });
    setValue(`items.${index}.service_id`, item.id);
    setValue(`items.${index}.unit_price_display`, String(item.default_price / 100), { shouldValidate: true });
    setIsOpen(false);
    setSearchTerm("");
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = (e.currentTarget as unknown as { value: string }).value;
    setValue(`items.${index}.description`, val, { shouldValidate: true });
    setSearchTerm(val);
    setHighlightedIndex(-1);
    if (val.length >= 2) {
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!isOpen || results.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && highlightedIndex >= 0) {
      e.preventDefault();
      handleSelect(results[highlightedIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  }

  // RHF register for validation, but we control the value
  const { ref, ...rest } = register(`items.${index}.description`);

  return (
    <div className="relative">
      <div className="relative">
        <Input
          ref={ref}
          {...rest}
          placeholder="Buscar servicio o escribir descripción"
          className="h-8 text-sm pr-7"
          disabled={disabled}
          onChange={handleInputChange}
          onFocus={() => {
            if (description.length >= 2) {
              setSearchTerm(description);
              setIsOpen(true);
            }
          }}
          onBlur={() => {
            // Delay to allow mousedown on option to fire first
            setTimeout(() => setIsOpen(false), 200);
          }}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />
        <Search className="absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute z-50 top-full left-0 w-full mt-1 max-h-48 overflow-y-auto rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--popover))] text-[hsl(var(--popover-foreground))] shadow-md">
          {results.map((item, i) => (
            <button
              key={item.id}
              type="button"
              className={`w-full text-left px-3 py-2 text-sm hover:bg-[hsl(var(--accent))] cursor-pointer flex flex-col gap-0.5 ${
                i === highlightedIndex ? "bg-[hsl(var(--accent))]" : ""
              }`}
              onMouseDown={(e) => {
                e.preventDefault();
                handleSelect(item);
              }}
              onMouseEnter={() => setHighlightedIndex(i)}
            >
              <span className="font-medium truncate">{item.name}</span>
              <span className="text-xs text-muted-foreground flex items-center gap-2">
                {item.cups_code && (
                  <span className="font-mono bg-[hsl(var(--muted))] px-1 rounded">
                    {item.cups_code}
                  </span>
                )}
                <span>{formatCurrency(item.default_price, "COP")}</span>
                {item.category && <span>· {item.category}</span>}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Line Items Editor ──────────────────────────────────────────────────────

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
                      <ServiceAutocomplete index={index} disabled={disabled} />
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
