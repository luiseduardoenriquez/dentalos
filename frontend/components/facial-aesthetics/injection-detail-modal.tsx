"use client";

import * as React from "react";
import { X, Loader2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { INJECTION_TYPE_LABELS, DEPTH_LABELS } from "@/lib/facial-aesthetics/zones";
import type { InjectionResponse } from "@/lib/hooks/use-facial-aesthetics";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface InjectionDetailModalProps {
  open: boolean;
  onClose: () => void;
  zoneId: string;
  zoneName: string;
  existingInjection: InjectionResponse | null;
  onSave: (data: Record<string, unknown>) => void;
  onRemove?: () => void;
  isSaving: boolean;
}

interface FormState {
  injection_type: string;
  product_name: string;
  dose_units: string;
  dose_volume_ml: string;
  depth: string;
  notes: string;
}

function buildInitialState(existing: InjectionResponse | null): FormState {
  if (existing) {
    return {
      injection_type: existing.injection_type ?? "botulinum_toxin",
      product_name: existing.product_name ?? "",
      dose_units: existing.dose_units !== null ? String(existing.dose_units) : "",
      dose_volume_ml:
        existing.dose_volume_ml !== null ? String(existing.dose_volume_ml) : "",
      depth: existing.depth ?? "",
      notes: existing.notes ?? "",
    };
  }
  return {
    injection_type: "botulinum_toxin",
    product_name: "",
    dose_units: "",
    dose_volume_ml: "",
    depth: "",
    notes: "",
  };
}

// ─── Label helper ─────────────────────────────────────────────────────────────

function FieldLabel({
  htmlFor,
  children,
  required,
}: {
  htmlFor: string;
  children: React.ReactNode;
  required?: boolean;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
    >
      {children}
      {required && (
        <span className="ml-0.5 text-red-500 dark:text-red-400" aria-hidden="true">
          *
        </span>
      )}
    </label>
  );
}

// ─── Select input ─────────────────────────────────────────────────────────────

const selectBase = [
  "flex h-10 w-full rounded-md border border-[hsl(var(--input))]",
  "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
  "transition-colors duration-150",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-0",
  "disabled:cursor-not-allowed disabled:opacity-50",
  "dark:border-[hsl(var(--input))] dark:bg-[hsl(var(--background))]",
].join(" ");

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Modal for adding or editing an injection point on a facial aesthetics zone.
 * - New injection: existingInjection is null.
 * - Edit mode: existingInjection carries the current data.
 */
export function InjectionDetailModal({
  open,
  onClose,
  zoneId: _zoneId,
  zoneName,
  existingInjection,
  onSave,
  onRemove,
  isSaving,
}: InjectionDetailModalProps) {
  const isEditing = existingInjection !== null;
  const modalRef = React.useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = React.useState(false);
  const [form, setForm] = React.useState<FormState>(() =>
    buildInitialState(existingInjection),
  );

  // Re-initialize form when modal opens or injection changes
  React.useEffect(() => {
    if (open) {
      setForm(buildInitialState(existingInjection));
      requestAnimationFrame(() => setIsVisible(true));
    } else {
      setIsVisible(false);
    }
  }, [open, existingInjection]);

  // Escape to close
  React.useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  // Focus trap
  React.useEffect(() => {
    if (!open) return;
    const modal = modalRef.current;
    if (!modal) return;

    const focusable = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first?.focus();

    function trapFocus(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }

    document.addEventListener("keydown", trapFocus);
    return () => document.removeEventListener("keydown", trapFocus);
  }, [open]);

  // ── Handlers ────────────────────────────────────────────────────────────────

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: Record<string, unknown> = {
      injection_type: form.injection_type,
    };
    if (form.product_name.trim()) {
      payload.product_name = form.product_name.trim();
    }
    if (form.dose_units !== "") {
      const parsed = parseFloat(form.dose_units);
      if (!isNaN(parsed)) payload.dose_units = parsed;
    }
    if (form.dose_volume_ml !== "") {
      const parsed = parseFloat(form.dose_volume_ml);
      if (!isNaN(parsed)) payload.dose_volume_ml = parsed;
    }
    if (form.depth) {
      payload.depth = form.depth;
    }
    if (form.notes.trim()) {
      payload.notes = form.notes.trim();
    }
    onSave(payload);
  }

  if (!open) return null;

  const title = isEditing ? "Editar inyección" : "Agregar inyección";

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center p-4",
        "transition-opacity duration-200 ease-out",
        isVisible ? "opacity-100" : "opacity-0",
      )}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-hidden="true"
      />

      {/* Modal card */}
      <div
        ref={modalRef}
        className={cn(
          "relative w-full max-w-md max-h-[90vh] overflow-y-auto",
          "rounded-xl border border-[hsl(var(--border))]",
          "bg-[hsl(var(--background))] p-6 shadow-2xl",
          "transition-transform duration-200 ease-out",
          isVisible ? "scale-100" : "scale-95",
        )}
      >
        {/* ── Header ────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{title}</h2>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
              Zona:{" "}
              <span className="font-medium text-foreground">{zoneName}</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              "rounded-lg p-2 transition-colors",
              "text-[hsl(var(--muted-foreground))] hover:text-foreground",
              "hover:bg-[hsl(var(--muted))]",
            )}
            aria-label="Cerrar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ── Form ──────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {/* Tipo de inyección */}
          <div>
            <FieldLabel htmlFor="injection_type" required>
              Tipo de inyección
            </FieldLabel>
            <select
              id="injection_type"
              name="injection_type"
              value={form.injection_type}
              onChange={handleChange}
              disabled={isSaving}
              className={selectBase}
            >
              {Object.entries(INJECTION_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Producto */}
          <div>
            <FieldLabel htmlFor="product_name">Producto</FieldLabel>
            <Input
              id="product_name"
              name="product_name"
              type="text"
              value={form.product_name}
              onChange={handleChange}
              maxLength={100}
              placeholder="Nombre comercial del producto"
              disabled={isSaving}
            />
          </div>

          {/* Dosis — two columns */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <FieldLabel htmlFor="dose_units">Unidades</FieldLabel>
              <Input
                id="dose_units"
                name="dose_units"
                type="number"
                value={form.dose_units}
                onChange={handleChange}
                min="0"
                step="0.1"
                placeholder="0.0"
                disabled={isSaving}
              />
            </div>
            <div>
              <FieldLabel htmlFor="dose_volume_ml">Volumen (ml)</FieldLabel>
              <Input
                id="dose_volume_ml"
                name="dose_volume_ml"
                type="number"
                value={form.dose_volume_ml}
                onChange={handleChange}
                min="0"
                step="0.01"
                placeholder="0.00"
                disabled={isSaving}
              />
            </div>
          </div>

          {/* Profundidad */}
          <div>
            <FieldLabel htmlFor="depth">Profundidad</FieldLabel>
            <select
              id="depth"
              name="depth"
              value={form.depth}
              onChange={handleChange}
              disabled={isSaving}
              className={selectBase}
            >
              <option value="">— Seleccionar —</option>
              {Object.entries(DEPTH_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Notas */}
          <div>
            <FieldLabel htmlFor="notes">Notas</FieldLabel>
            <textarea
              id="notes"
              name="notes"
              value={form.notes}
              onChange={handleChange}
              maxLength={500}
              rows={3}
              placeholder="Observaciones o indicaciones adicionales..."
              disabled={isSaving}
              className={cn(
                "flex w-full rounded-md border border-[hsl(var(--input))]",
                "bg-[hsl(var(--background))] px-3 py-2",
                "text-sm text-foreground placeholder:text-[hsl(var(--muted-foreground))]",
                "shadow-sm transition-colors resize-none",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
                "disabled:cursor-not-allowed disabled:opacity-50",
                "dark:border-[hsl(var(--input))] dark:bg-[hsl(var(--background))]",
              )}
            />
            <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))] text-right">
              {form.notes.length}/500
            </p>
          </div>

          {/* ── Footer buttons ──────────────────────────────────────── */}
          <div
            className={cn(
              "flex items-center gap-2 pt-2",
              isEditing ? "justify-between" : "justify-end",
            )}
          >
            {/* Eliminar — only in edit mode */}
            {isEditing && onRemove && (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={onRemove}
                disabled={isSaving}
                aria-label="Eliminar inyección"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Eliminar
              </Button>
            )}

            <div className="flex items-center gap-2 ml-auto">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onClose}
                disabled={isSaving}
              >
                Cancelar
              </Button>

              <Button
                type="submit"
                variant="default"
                size="sm"
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  "Guardar"
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

InjectionDetailModal.displayName = "InjectionDetailModal";
