"use client";

import * as React from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { EPSClaimCreate, EPSClaimProcedure } from "@/lib/hooks/use-eps-claims";

// ─── Constants ────────────────────────────────────────────────────────────────

const CLAIM_TYPE_LABELS: Record<EPSClaimCreate["claim_type"], string> = {
  ambulatorio: "Ambulatorio",
  urgencias: "Urgencias",
  hospitalizacion: "Hospitalización",
  dental: "Dental",
};

// ─── Empty procedure factory ──────────────────────────────────────────────────

function emptyProcedure(): EPSClaimProcedure {
  return {
    cups_code: "",
    description: "",
    quantity: 1,
    unit_price_cents: 0,
  };
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface EPSClaimFormProps {
  onSubmit: (data: EPSClaimCreate) => void;
  isLoading: boolean;
  defaultValues?: Partial<EPSClaimCreate>;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Form for creating or editing an EPS claim.
 *
 * Includes a dynamic procedures array with add/remove functionality.
 */
export function EPSClaimForm({
  onSubmit,
  isLoading,
  defaultValues,
}: EPSClaimFormProps) {
  const [patientId, setPatientId] = React.useState(
    defaultValues?.patient_id ?? "",
  );
  const [epsCode, setEpsCode] = React.useState(defaultValues?.eps_code ?? "");
  const [epsName, setEpsName] = React.useState(defaultValues?.eps_name ?? "");
  const [claimType, setClaimType] = React.useState<EPSClaimCreate["claim_type"]>(
    defaultValues?.claim_type ?? "ambulatorio",
  );
  const [totalAmountCents, setTotalAmountCents] = React.useState(
    defaultValues?.total_amount_cents ?? 0,
  );
  const [copayAmountCents, setCopayAmountCents] = React.useState(
    defaultValues?.copay_amount_cents ?? 0,
  );
  const [procedures, setProcedures] = React.useState<EPSClaimProcedure[]>(
    defaultValues?.procedures?.length
      ? defaultValues.procedures
      : [emptyProcedure()],
  );

  // ─── Procedures handlers ─────────────────────────────────────────────────

  function addProcedure() {
    setProcedures((prev) => [...prev, emptyProcedure()]);
  }

  function removeProcedure(index: number) {
    setProcedures((prev) => prev.filter((_, i) => i !== index));
  }

  function updateProcedure<K extends keyof EPSClaimProcedure>(
    index: number,
    field: K,
    value: EPSClaimProcedure[K],
  ) {
    setProcedures((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)),
    );
  }

  // ─── Submit ──────────────────────────────────────────────────────────────

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      patient_id: patientId.trim(),
      eps_code: epsCode.trim(),
      eps_name: epsName.trim(),
      claim_type: claimType,
      total_amount_cents: totalAmountCents,
      copay_amount_cents: copayAmountCents,
      procedures: procedures.filter(
        (p) => p.cups_code.trim() !== "" || p.description.trim() !== "",
      ),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* ── Basic info ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Patient ID */}
        <div className="space-y-1.5">
          <Label htmlFor="eps-patient-id">ID del paciente</Label>
          <Input
            id="eps-patient-id"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            placeholder="UUID del paciente"
            required
            disabled={isLoading}
          />
        </div>

        {/* Claim type */}
        <div className="space-y-1.5">
          <Label htmlFor="eps-claim-type">Tipo de reclamación</Label>
          <Select
            value={claimType}
            onValueChange={(v) => setClaimType(v as EPSClaimCreate["claim_type"])}
            disabled={isLoading}
          >
            <SelectTrigger id="eps-claim-type">
              <SelectValue placeholder="Selecciona el tipo" />
            </SelectTrigger>
            <SelectContent>
              {(
                Object.entries(CLAIM_TYPE_LABELS) as [
                  EPSClaimCreate["claim_type"],
                  string,
                ][]
              ).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* EPS code */}
        <div className="space-y-1.5">
          <Label htmlFor="eps-code">Código EPS</Label>
          <Input
            id="eps-code"
            value={epsCode}
            onChange={(e) => setEpsCode(e.target.value)}
            placeholder="Ej. SURA, SALUD_TOTAL"
            required
            disabled={isLoading}
          />
        </div>

        {/* EPS name */}
        <div className="space-y-1.5">
          <Label htmlFor="eps-name">Nombre de la EPS</Label>
          <Input
            id="eps-name"
            value={epsName}
            onChange={(e) => setEpsName(e.target.value)}
            placeholder="Ej. Sura EPS"
            required
            disabled={isLoading}
          />
        </div>

        {/* Total amount */}
        <div className="space-y-1.5">
          <Label htmlFor="eps-total">Valor total (centavos COP)</Label>
          <Input
            id="eps-total"
            type="number"
            min={0}
            value={totalAmountCents}
            onChange={(e) =>
              setTotalAmountCents(parseInt(e.target.value, 10) || 0)
            }
            placeholder="Ej. 150000"
            required
            disabled={isLoading}
          />
        </div>

        {/* Copay amount */}
        <div className="space-y-1.5">
          <Label htmlFor="eps-copay">Copago (centavos COP)</Label>
          <Input
            id="eps-copay"
            type="number"
            min={0}
            value={copayAmountCents}
            onChange={(e) =>
              setCopayAmountCents(parseInt(e.target.value, 10) || 0)
            }
            placeholder="Ej. 15000"
            disabled={isLoading}
          />
        </div>
      </div>

      {/* ── Procedures ─────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">
            Procedimientos
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addProcedure}
            disabled={isLoading}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Agregar procedimiento
          </Button>
        </div>

        <div className="space-y-3">
          {procedures.map((proc, index) => (
            <div
              key={index}
              className={cn(
                "rounded-lg border border-[hsl(var(--border))] p-4",
                "bg-[hsl(var(--muted)/30%)]",
              )}
            >
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {/* CUPS code */}
                <div className="space-y-1.5">
                  <Label
                    htmlFor={`proc-cups-${index}`}
                    className="text-xs"
                  >
                    Código CUPS
                  </Label>
                  <Input
                    id={`proc-cups-${index}`}
                    value={proc.cups_code}
                    onChange={(e) =>
                      updateProcedure(index, "cups_code", e.target.value)
                    }
                    placeholder="Ej. 890201"
                    className="h-8 text-sm"
                    disabled={isLoading}
                  />
                </div>

                {/* Description */}
                <div className="space-y-1.5">
                  <Label
                    htmlFor={`proc-desc-${index}`}
                    className="text-xs"
                  >
                    Descripción
                  </Label>
                  <Input
                    id={`proc-desc-${index}`}
                    value={proc.description}
                    onChange={(e) =>
                      updateProcedure(index, "description", e.target.value)
                    }
                    placeholder="Nombre del procedimiento"
                    className="h-8 text-sm"
                    disabled={isLoading}
                  />
                </div>

                {/* Quantity */}
                <div className="space-y-1.5">
                  <Label
                    htmlFor={`proc-qty-${index}`}
                    className="text-xs"
                  >
                    Cantidad
                  </Label>
                  <Input
                    id={`proc-qty-${index}`}
                    type="number"
                    min={1}
                    value={proc.quantity}
                    onChange={(e) =>
                      updateProcedure(
                        index,
                        "quantity",
                        parseInt(e.target.value, 10) || 1,
                      )
                    }
                    className="h-8 text-sm"
                    disabled={isLoading}
                  />
                </div>

                {/* Unit price */}
                <div className="space-y-1.5">
                  <Label
                    htmlFor={`proc-price-${index}`}
                    className="text-xs"
                  >
                    Precio unitario (centavos)
                  </Label>
                  <Input
                    id={`proc-price-${index}`}
                    type="number"
                    min={0}
                    value={proc.unit_price_cents}
                    onChange={(e) =>
                      updateProcedure(
                        index,
                        "unit_price_cents",
                        parseInt(e.target.value, 10) || 0,
                      )
                    }
                    className="h-8 text-sm"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Remove button */}
              {procedures.length > 1 && (
                <div className="mt-3 flex justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeProcedure(index)}
                    disabled={isLoading}
                    className="h-7 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Eliminar
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Submit ─────────────────────────────────────────────────────────── */}
      <div className="flex justify-end">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Guardando..." : "Guardar borrador"}
        </Button>
      </div>
    </form>
  );
}
