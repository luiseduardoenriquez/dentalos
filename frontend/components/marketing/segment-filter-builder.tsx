"use client";

import * as React from "react";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SegmentFilters {
  last_visit_before?: string;
  last_visit_after?: string;
  age_min?: number;
  age_max?: number;
  insurance_type?: string;
  has_balance_due?: boolean;
}

type FilterKey = keyof SegmentFilters;

interface FilterDefinition {
  key: FilterKey;
  label: string;
  description: string;
  type: "date" | "number" | "select" | "checkbox";
  selectOptions?: { value: string; label: string }[];
}

const FILTER_DEFINITIONS: FilterDefinition[] = [
  {
    key: "last_visit_after",
    label: "Última visita desde",
    description: "Pacientes cuya última visita fue a partir de esta fecha",
    type: "date",
  },
  {
    key: "last_visit_before",
    label: "Última visita hasta",
    description: "Pacientes cuya última visita fue antes de esta fecha",
    type: "date",
  },
  {
    key: "age_min",
    label: "Edad mínima",
    description: "Pacientes con esta edad o más",
    type: "number",
  },
  {
    key: "age_max",
    label: "Edad máxima",
    description: "Pacientes con esta edad o menos",
    type: "number",
  },
  {
    key: "insurance_type",
    label: "Tipo de seguro",
    description: "Filtrar por tipo de cobertura del paciente",
    type: "select",
    selectOptions: [
      { value: "eps", label: "EPS" },
      { value: "particular", label: "Particular" },
      { value: "prepagada", label: "Medicina prepagada" },
      { value: "arl", label: "ARL" },
      { value: "convenio", label: "Convenio" },
    ],
  },
  {
    key: "has_balance_due",
    label: "Con saldo pendiente",
    description: "Solo pacientes que tienen facturas por pagar",
    type: "checkbox",
  },
];

interface SegmentFilterBuilderProps {
  filters: SegmentFilters;
  onChange: (filters: SegmentFilters) => void;
}

// ─── SegmentFilterBuilder ─────────────────────────────────────────────────────

export function SegmentFilterBuilder({
  filters,
  onChange,
}: SegmentFilterBuilderProps) {
  const activeKeys = Object.keys(filters).filter(
    (k) => filters[k as FilterKey] !== undefined && filters[k as FilterKey] !== null,
  ) as FilterKey[];

  const availableToAdd = FILTER_DEFINITIONS.filter(
    (d) => !activeKeys.includes(d.key),
  );

  function addFilter(key: FilterKey) {
    const def = FILTER_DEFINITIONS.find((d) => d.key === key);
    if (!def) return;

    let defaultValue: SegmentFilters[FilterKey];
    if (def.type === "date") defaultValue = "";
    else if (def.type === "number") defaultValue = undefined;
    else if (def.type === "select") defaultValue = "";
    else if (def.type === "checkbox") defaultValue = false;

    onChange({ ...filters, [key]: defaultValue });
  }

  function removeFilter(key: FilterKey) {
    const updated = { ...filters };
    delete updated[key];
    onChange(updated);
  }

  function updateFilter(key: FilterKey, value: SegmentFilters[FilterKey]) {
    onChange({ ...filters, [key]: value });
  }

  const activeFilterCount = activeKeys.length;

  return (
    <div className="flex flex-col gap-4">
      {/* Active filters */}
      {activeFilterCount === 0 && (
        <div className="rounded-md border border-dashed border-[hsl(var(--border))] py-8 text-center text-[hsl(var(--muted-foreground))]">
          <p className="text-sm">Sin filtros activos</p>
          <p className="text-xs mt-1">
            Se enviará a todos los pacientes activos con email
          </p>
        </div>
      )}

      {activeKeys.map((key) => {
        const def = FILTER_DEFINITIONS.find((d) => d.key === key);
        if (!def) return null;

        return (
          <FilterRow
            key={key}
            definition={def}
            value={filters[key]}
            onUpdate={(v) => updateFilter(key, v)}
            onRemove={() => removeFilter(key)}
          />
        );
      })}

      {/* Add filter button */}
      {availableToAdd.length > 0 && (
        <AddFilterDropdown
          available={availableToAdd}
          onAdd={addFilter}
        />
      )}

      {/* Summary */}
      {activeFilterCount > 0 && (
        <div className="rounded-md bg-[hsl(var(--muted))] px-4 py-3">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            <span className="font-medium text-foreground">
              {activeFilterCount} {activeFilterCount === 1 ? "filtro activo" : "filtros activos"}
            </span>
            {" "}— La campaña se enviará solo a los pacientes que cumplan todos los criterios.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── FilterRow ────────────────────────────────────────────────────────────────

interface FilterRowProps {
  definition: FilterDefinition;
  value: SegmentFilters[FilterKey];
  onUpdate: (value: SegmentFilters[FilterKey]) => void;
  onRemove: () => void;
}

function FilterRow({ definition, value, onUpdate, onRemove }: FilterRowProps) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
      {/* Filter control */}
      <div className="flex-1 grid sm:grid-cols-2 gap-3 items-center">
        <div>
          <Label className="text-sm font-medium">{definition.label}</Label>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
            {definition.description}
          </p>
        </div>

        <div>
          {definition.type === "date" && (
            <input
              type="date"
              value={typeof value === "string" ? value : ""}
              onChange={(e) => onUpdate(e.target.value)}
              className={cn(
                "flex h-9 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
                "px-3 py-1 text-sm shadow-sm transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
              )}
            />
          )}

          {definition.type === "number" && (
            <Input
              type="number"
              min={0}
              max={120}
              value={typeof value === "number" ? value : ""}
              onChange={(e) =>
                onUpdate(e.target.value ? parseInt(e.target.value, 10) : undefined)
              }
              placeholder="Ej: 18"
            />
          )}

          {definition.type === "select" && definition.selectOptions && (
            <Select
              value={typeof value === "string" ? value : ""}
              onValueChange={(v) => onUpdate(v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecciona..." />
              </SelectTrigger>
              <SelectContent>
                {definition.selectOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {definition.type === "checkbox" && (
            <div className="flex items-center gap-2 h-9">
              <Checkbox
                id={`filter-${definition.key}`}
                checked={typeof value === "boolean" ? value : false}
                onCheckedChange={(checked) => onUpdate(Boolean(checked))}
              />
              <label
                htmlFor={`filter-${definition.key}`}
                className="text-sm cursor-pointer"
              >
                Activar filtro
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Remove button */}
      <button
        type="button"
        onClick={onRemove}
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md mt-1",
          "text-[hsl(var(--muted-foreground))] hover:text-red-600 hover:bg-red-50",
          "dark:hover:bg-red-900/20 transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-600",
        )}
        aria-label={`Eliminar filtro ${definition.label}`}
        title="Eliminar filtro"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ─── AddFilterDropdown ────────────────────────────────────────────────────────

interface AddFilterDropdownProps {
  available: FilterDefinition[];
  onAdd: (key: FilterKey) => void;
}

function AddFilterDropdown({ available, onAdd }: AddFilterDropdownProps) {
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Close on outside click
  React.useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div ref={containerRef} className="relative w-fit">
      <Button
        variant="outline"
        size="sm"
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="gap-1.5"
      >
        <Plus className="h-3.5 w-3.5" />
        Agregar filtro
      </Button>

      {open && (
        <div
          className={cn(
            "absolute top-full left-0 mt-1 z-10 min-w-56",
            "rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] shadow-md",
            "overflow-hidden",
          )}
        >
          {available.map((def) => (
            <button
              key={def.key}
              type="button"
              onClick={() => {
                onAdd(def.key);
                setOpen(false);
              }}
              className={cn(
                "w-full flex flex-col items-start gap-0.5 px-4 py-2.5 text-left",
                "hover:bg-[hsl(var(--muted))] transition-colors text-sm",
              )}
            >
              <span className="font-medium">{def.label}</span>
              <span className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-1">
                {def.description}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
