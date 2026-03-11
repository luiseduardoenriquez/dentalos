"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChevronRight, AlertCircle, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/empty-state";
import { usePatient } from "@/lib/hooks/use-patients";
import { useOrthoCase, useCreateBondingRecord } from "@/lib/hooks/use-ortho";
import type { BondingToothInput } from "@/lib/hooks/use-ortho";
import {
  BRACKET_TYPE_LABELS,
  BRACKET_STATUS_LABELS,
} from "@/lib/validations/ortho";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

// FDI permanent dentition for orthodontics
// Upper arch: right quadrant first (patient's right = our left visually)
const UPPER_RIGHT = [18, 17, 16, 15, 14, 13, 12, 11];
const UPPER_LEFT = [21, 22, 23, 24, 25, 26, 27, 28];
// Lower arch: right quadrant first
const LOWER_RIGHT = [48, 47, 46, 45, 44, 43, 42, 41];
const LOWER_LEFT = [31, 32, 33, 34, 35, 36, 37, 38];

const BRACKET_STATUSES = ["bonded", "pending", "removed", "not_applicable"] as const;
const BRACKET_TYPES = ["metalico", "ceramico", "autoligado", "lingual"] as const;
const SLOT_SIZES = ["0.022", "0.018"] as const;

// ─── Tooth color by bracket_status ───────────────────────────────────────────

const TOOTH_STATUS_STYLES: Record<string, string> = {
  bonded:
    "bg-green-500 hover:bg-green-600 text-white border-green-600 dark:bg-green-600 dark:hover:bg-green-500 dark:border-green-500",
  pending:
    "bg-[hsl(var(--muted))] hover:bg-[hsl(var(--muted-foreground)/0.15)] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
  removed:
    "bg-red-400 hover:bg-red-500 text-white border-red-500 dark:bg-red-500 dark:hover:bg-red-400 dark:border-red-400",
  not_applicable:
    "bg-slate-200 text-slate-400 border-slate-300 dark:bg-slate-700 dark:text-slate-500 dark:border-slate-600 line-through",
};

// ─── Types ────────────────────────────────────────────────────────────────────

type TeethState = Record<number, BondingToothInput>;

// ─── Popover-style inline panel for a tooth ───────────────────────────────────
// Since @radix-ui/react-popover is installed but there is no pre-built
// Popover component file in components/ui/, we use the primitive directly.

import * as PopoverPrimitive from "@radix-ui/react-popover";

function ToothPopover({
  toothNumber,
  data,
  onChange,
}: {
  toothNumber: number;
  data: BondingToothInput;
  onChange: (updated: BondingToothInput) => void;
}) {
  const status = data.bracket_status;

  function setStatus(s: string) {
    onChange({ ...data, bracket_status: s });
  }

  function setBracketType(t: string) {
    onChange({ ...data, bracket_type: t });
  }

  function setSlotSize(s: string) {
    onChange({ ...data, slot_size: s });
  }

  function setBand(checked: boolean) {
    onChange({ ...data, band: checked });
  }

  return (
    <PopoverPrimitive.Root>
      <PopoverPrimitive.Trigger asChild>
        <button
          type="button"
          title={`Diente ${toothNumber} — ${BRACKET_STATUS_LABELS[status] ?? status}`}
          aria-label={`Diente ${toothNumber}`}
          className={cn(
            "relative flex h-12 w-12 flex-col items-center justify-center rounded-md border text-xs font-semibold",
            "transition-colors duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
            TOOTH_STATUS_STYLES[status] ?? TOOTH_STATUS_STYLES.pending,
          )}
        >
          <span className="tabular-nums leading-tight">{toothNumber}</span>
          {status === "bonded" && (
            <span className="absolute bottom-0.5 left-0 right-0 text-center text-[8px] leading-none opacity-70 font-normal">
              cmt
            </span>
          )}
          {status === "not_applicable" && (
            <span className="absolute inset-0 flex items-center justify-center text-base font-bold opacity-40">
              ✕
            </span>
          )}
        </button>
      </PopoverPrimitive.Trigger>

      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="bottom"
          align="center"
          sideOffset={6}
          className={cn(
            "z-50 w-64 rounded-lg border border-[hsl(var(--border))]",
            "bg-[hsl(var(--popover))] text-[hsl(var(--popover-foreground))]",
            "p-4 shadow-lg",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
            "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
            "data-[side=bottom]:slide-in-from-top-2",
          )}
        >
          <p className="mb-3 text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
            Diente {toothNumber}
          </p>

          {/* bracket_status: radio buttons */}
          <div className="space-y-1 mb-3">
            <Label className="text-xs text-[hsl(var(--muted-foreground))]">
              Estado del bracket
            </Label>
            <div className="grid grid-cols-2 gap-1 pt-1">
              {BRACKET_STATUSES.map((s) => {
                const isActive = status === s;
                const dotColors: Record<string, string> = {
                  bonded: "bg-green-500",
                  pending: "bg-[hsl(var(--muted-foreground))]",
                  removed: "bg-red-400",
                  not_applicable: "bg-slate-400",
                };
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setStatus(s)}
                    className={cn(
                      "flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium",
                      "border transition-colors duration-100",
                      isActive
                        ? "border-primary-600 bg-primary-600/10 text-primary-600 dark:bg-primary-600/20"
                        : "border-[hsl(var(--border))] text-foreground hover:bg-[hsl(var(--muted))]",
                    )}
                  >
                    <span
                      className={cn(
                        "h-2 w-2 rounded-full shrink-0",
                        dotColors[s],
                      )}
                    />
                    {BRACKET_STATUS_LABELS[s]}
                  </button>
                );
              })}
            </div>
          </div>

          {/* bracket_type: only when bonded */}
          {status === "bonded" && (
            <div className="space-y-1 mb-3">
              <Label
                htmlFor={`bracket-type-${toothNumber}`}
                className="text-xs text-[hsl(var(--muted-foreground))]"
              >
                Tipo de bracket
              </Label>
              <Select
                value={data.bracket_type ?? ""}
                onValueChange={setBracketType}
              >
                <SelectTrigger
                  id={`bracket-type-${toothNumber}`}
                  className="h-8 text-xs"
                >
                  <SelectValue placeholder="Seleccionar tipo" />
                </SelectTrigger>
                <SelectContent>
                  {BRACKET_TYPES.map((t) => (
                    <SelectItem key={t} value={t} className="text-xs">
                      {BRACKET_TYPE_LABELS[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* slot_size */}
          {status === "bonded" && (
            <div className="space-y-1 mb-3">
              <Label
                htmlFor={`slot-size-${toothNumber}`}
                className="text-xs text-[hsl(var(--muted-foreground))]"
              >
                Tamaño de slot
              </Label>
              <Select
                value={data.slot_size ?? ""}
                onValueChange={setSlotSize}
              >
                <SelectTrigger
                  id={`slot-size-${toothNumber}`}
                  className="h-8 text-xs"
                >
                  <SelectValue placeholder="Seleccionar slot" />
                </SelectTrigger>
                <SelectContent>
                  {SLOT_SIZES.map((s) => (
                    <SelectItem key={s} value={s} className="text-xs">
                      {s}&quot;
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* band */}
          {status === "bonded" && (
            <div className="flex items-center gap-2">
              <Checkbox
                id={`band-${toothNumber}`}
                checked={data.band ?? false}
                onCheckedChange={(v) => setBand(Boolean(v))}
              />
              <label
                htmlFor={`band-${toothNumber}`}
                className="text-xs font-medium text-foreground cursor-pointer"
              >
                Banda en lugar de bracket
              </label>
            </div>
          )}

          <PopoverPrimitive.Arrow className="fill-[hsl(var(--border))]" />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

// ─── Tooth Row ────────────────────────────────────────────────────────────────

function ToothRow({
  label,
  leftTeeth,
  rightTeeth,
  teethState,
  onToothChange,
}: {
  label: string;
  leftTeeth: readonly number[];
  rightTeeth: readonly number[];
  teethState: TeethState;
  onToothChange: (toothNumber: number, data: BondingToothInput) => void;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide pl-1">
        {label}
      </p>
      <div className="flex items-center gap-1 flex-wrap">
        {leftTeeth.map((t) => (
          <ToothPopover
            key={t}
            toothNumber={t}
            data={
              teethState[t] ?? {
                tooth_number: t,
                bracket_status: "pending",
              }
            }
            onChange={(updated) => onToothChange(t, updated)}
          />
        ))}

        {/* Midline divider */}
        <div className="w-px h-12 bg-[hsl(var(--border))] mx-1 shrink-0" />

        {rightTeeth.map((t) => (
          <ToothPopover
            key={t}
            toothNumber={t}
            data={
              teethState[t] ?? {
                tooth_number: t,
                bracket_status: "pending",
              }
            }
            onChange={(updated) => onToothChange(t, updated)}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Bonding Chart ────────────────────────────────────────────────────────────

function BondingChart({
  teethState,
  onToothChange,
}: {
  teethState: TeethState;
  onToothChange: (toothNumber: number, data: BondingToothInput) => void;
}) {
  // Quick-select all teeth to a given status
  function applyAllStatus(status: string) {
    const allTeeth = [
      ...UPPER_RIGHT,
      ...UPPER_LEFT,
      ...LOWER_RIGHT,
      ...LOWER_LEFT,
    ];
    allTeeth.forEach((t) => {
      onToothChange(t, {
        tooth_number: t,
        bracket_status: status,
        bracket_type: status === "bonded" ? teethState[t]?.bracket_type : undefined,
        slot_size: status === "bonded" ? teethState[t]?.slot_size : undefined,
        band: status === "bonded" ? (teethState[t]?.band ?? false) : false,
      });
    });
  }

  return (
    <div className="space-y-5">
      {/* Legend + Quick actions */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-4">
          {(
            [
              { status: "bonded", label: "Cementado", color: "bg-green-500" },
              { status: "pending", label: "Pendiente", color: "bg-[hsl(var(--muted-foreground))]" },
              { status: "removed", label: "Removido", color: "bg-red-400" },
              { status: "not_applicable", label: "No aplica", color: "bg-slate-400" },
            ] as const
          ).map(({ status, label, color }) => (
            <div key={status} className="flex items-center gap-1.5">
              <span className={cn("h-3 w-3 rounded-sm", color)} />
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                {label}
              </span>
            </div>
          ))}
        </div>
        <div className="ml-auto flex gap-1.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => applyAllStatus("bonded")}
          >
            Todos cementados
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => applyAllStatus("pending")}
          >
            Limpiar
          </Button>
        </div>
      </div>

      {/* Grid */}
      <div className="space-y-4 overflow-x-auto pb-2">
        <ToothRow
          label="Arcada superior"
          leftTeeth={UPPER_RIGHT}
          rightTeeth={UPPER_LEFT}
          teethState={teethState}
          onToothChange={onToothChange}
        />
        <div className="border-t border-dashed border-[hsl(var(--border))]" />
        <ToothRow
          label="Arcada inferior"
          leftTeeth={LOWER_RIGHT}
          rightTeeth={LOWER_LEFT}
          teethState={teethState}
          onToothChange={onToothChange}
        />
      </div>

      {/* Stats */}
      <div className="flex gap-4 text-xs text-[hsl(var(--muted-foreground))]">
        {(
          ["bonded", "pending", "removed", "not_applicable"] as const
        ).map((s) => {
          const count = Object.values(teethState).filter(
            (t) => t.bracket_status === s,
          ).length;
          if (count === 0) return null;
          return (
            <span key={s}>
              <span className="font-semibold text-foreground">{count}</span>{" "}
              {BRACKET_STATUS_LABELS[s]?.toLowerCase()}
            </span>
          );
        })}
        {Object.keys(teethState).length === 0 && (
          <span>Haz clic en un diente para configurarlo</span>
        )}
      </div>
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function NewBondingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        {[16, 4, 28, 4, 24, 4, 24, 4, 32].map((w, i) => (
          <Skeleton key={i} className={`h-4 w-${w}`} />
        ))}
      </div>
      <Skeleton className="h-6 w-56" />
      <Skeleton className="h-24 w-full rounded-xl" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewBondingRecordPage() {
  const params = useParams<{ id: string; caseId: string }>();
  const router = useRouter();
  const { id: patientId, caseId } = params;

  const [notes, setNotes] = React.useState("");
  const [teethState, setTeethState] = React.useState<TeethState>({});
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: orthoCase, isLoading: isLoadingCase } = useOrthoCase(
    patientId,
    caseId,
  );
  const { mutate: createBonding, isPending } = useCreateBondingRecord(
    patientId,
    caseId,
  );

  function handleToothChange(toothNumber: number, data: BondingToothInput) {
    setTeethState((prev) => ({
      ...prev,
      [toothNumber]: { ...data, tooth_number: toothNumber },
    }));
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitError(null);

    // Collect all configured teeth; teeth not in teethState are implicitly "pending"
    // Only include teeth that have been explicitly configured (any state)
    const teeth = Object.values(teethState);

    if (teeth.length === 0) {
      setSubmitError(
        "Debes configurar al menos un diente antes de guardar.",
      );
      return;
    }

    createBonding(
      {
        notes: notes.trim() || null,
        teeth: teeth.map((t) => ({
          tooth_number: t.tooth_number,
          bracket_status: t.bracket_status,
          bracket_type:
            t.bracket_status === "bonded" ? (t.bracket_type ?? null) : null,
          slot_size:
            t.bracket_status === "bonded" ? (t.slot_size ?? null) : null,
          band: t.bracket_status === "bonded" ? (t.band ?? false) : false,
          notes: null,
        })),
      },
      {
        onSuccess: () => {
          router.push(`/patients/${patientId}/ortho/${caseId}`);
        },
      },
    );
  }

  const isLoading = isLoadingPatient || isLoadingCase;

  if (isLoading) {
    return <NewBondingSkeleton />;
  }

  if (!patient || !orthoCase) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Caso no encontrado"
        description="El caso de ortodoncia que buscas no existe o no tienes permiso para verlo."
        action={{
          label: "Volver",
          href: `/patients/${patientId}/ortho`,
        }}
      />
    );
  }

  const configuredCount = Object.keys(teethState).length;

  return (
    <div className="space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link
          href="/patients"
          className="hover:text-foreground transition-colors"
        >
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}`}
          className="hover:text-foreground transition-colors truncate max-w-[130px]"
        >
          {patient.full_name}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}/ortho`}
          className="hover:text-foreground transition-colors"
        >
          Ortodoncia
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}/ortho/${caseId}`}
          className="hover:text-foreground transition-colors"
        >
          {orthoCase.case_number}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nueva aparatología</span>
      </nav>

      {/* ─── Heading ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Stethoscope className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">
          Registro de aparatología
        </h1>
      </div>

      {/* ─── Form ────────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        {/* Notes */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Notas del registro
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              <Label htmlFor="bonding-notes">Observaciones generales</Label>
              <textarea
                id="bonding-notes"
                rows={2}
                placeholder="Ej. Cementado inicial con brackets metálicos Roth 0.022&quot;..."
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={isPending}
                maxLength={2000}
              />
              <p className="text-xs text-[hsl(var(--muted-foreground))] text-right">
                {notes.length}/2000
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Bonding Chart */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold">
                Diagrama de cementado
              </CardTitle>
              {configuredCount > 0 && (
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                  {configuredCount}{" "}
                  {configuredCount === 1
                    ? "diente configurado"
                    : "dientes configurados"}
                </span>
              )}
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
              Haz clic en cada diente para registrar el estado del bracket.
              Los dientes sin configurar no se incluirán en el registro.
            </p>
          </CardHeader>
          <CardContent>
            <BondingChart
              teethState={teethState}
              onToothChange={handleToothChange}
            />
          </CardContent>
        </Card>

        {/* Validation error */}
        {submitError && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3">
            <p className="text-sm text-destructive">{submitError}</p>
          </div>
        )}

        {/* Submit */}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              router.push(`/patients/${patientId}/ortho/${caseId}`)
            }
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={isPending || configuredCount === 0}
            className="min-w-[150px]"
          >
            {isPending ? "Guardando..." : "Guardar registro"}
          </Button>
        </div>
      </form>
    </div>
  );
}
