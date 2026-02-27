"use client";

import * as React from "react";
import { Plus, RefreshCw, CheckCircle2, XCircle, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useSterilizationRecords,
  useCreateSterilization,
  type SterilizationRecordCreate,
} from "@/lib/hooks/use-inventory";
import { cn } from "@/lib/utils";

// ─── Initial form state ───────────────────────────────────────────────────────

const INITIAL_FORM: SterilizationRecordCreate = {
  autoclave_id: "",
  load_number: "",
  date: "",
  temperature_celsius: undefined,
  duration_minutes: undefined,
  biological_indicator: "",
  chemical_indicator: "",
  responsible_user_id: "",
  is_compliant: true,
  instrument_ids: [],
  signature_data: "",
  notes: "",
};

// ─── Create Sterilization Dialog ──────────────────────────────────────────────

function CreateSterilizationDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [form, setForm] = React.useState<SterilizationRecordCreate>(INITIAL_FORM);
  // instrument_ids as comma-separated string in UI
  const [instrumentIdsRaw, setInstrumentIdsRaw] = React.useState("");
  const createMutation = useCreateSterilization();

  function handleChange(
    field: keyof SterilizationRecordCreate,
    value: string | number | boolean | undefined,
  ) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const instrumentIds = instrumentIdsRaw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const payload: SterilizationRecordCreate = {
      autoclave_id: form.autoclave_id.trim(),
      load_number: form.load_number.trim(),
      date: form.date,
      responsible_user_id: form.responsible_user_id.trim(),
      is_compliant: form.is_compliant,
      ...(form.temperature_celsius !== undefined && {
        temperature_celsius: Number(form.temperature_celsius),
      }),
      ...(form.duration_minutes !== undefined && {
        duration_minutes: Number(form.duration_minutes),
      }),
      ...(form.biological_indicator?.trim() && {
        biological_indicator: form.biological_indicator.trim(),
      }),
      ...(form.chemical_indicator?.trim() && {
        chemical_indicator: form.chemical_indicator.trim(),
      }),
      ...(instrumentIds.length > 0 && { instrument_ids: instrumentIds }),
      ...(form.signature_data?.trim() && {
        signature_data: form.signature_data.trim(),
      }),
      ...(form.notes?.trim() && { notes: form.notes.trim() }),
    };

    createMutation.mutate(payload, {
      onSuccess: () => {
        setForm(INITIAL_FORM);
        setInstrumentIdsRaw("");
        onOpenChange(false);
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nuevo registro de esterilización</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-2">
          {/* Autoclave + Load number */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-autoclave">
                Autoclave ID <span className="text-red-500">*</span>
              </Label>
              <Input
                id="st-autoclave"
                value={form.autoclave_id}
                onChange={(e) => handleChange("autoclave_id", e.target.value)}
                placeholder="Ej. AUT-01"
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-load">
                Número de carga <span className="text-red-500">*</span>
              </Label>
              <Input
                id="st-load"
                value={form.load_number}
                onChange={(e) => handleChange("load_number", e.target.value)}
                placeholder="Ej. CARGA-2026-001"
                required
              />
            </div>
          </div>

          {/* Date + Responsible user */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-date">
                Fecha <span className="text-red-500">*</span>
              </Label>
              <Input
                id="st-date"
                type="date"
                value={form.date}
                onChange={(e) => handleChange("date", e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-responsible">
                Responsable (ID usuario) <span className="text-red-500">*</span>
              </Label>
              <Input
                id="st-responsible"
                value={form.responsible_user_id}
                onChange={(e) => handleChange("responsible_user_id", e.target.value)}
                placeholder="UUID del usuario"
                required
              />
            </div>
          </div>

          {/* Temperature + Duration */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-temp">Temperatura (°C)</Label>
              <Input
                id="st-temp"
                type="number"
                min={0}
                step="0.1"
                value={form.temperature_celsius ?? ""}
                onChange={(e) =>
                  handleChange(
                    "temperature_celsius",
                    e.target.value === "" ? undefined : Number(e.target.value),
                  )
                }
                placeholder="Ej. 134"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-duration">Duración (minutos)</Label>
              <Input
                id="st-duration"
                type="number"
                min={0}
                value={form.duration_minutes ?? ""}
                onChange={(e) =>
                  handleChange(
                    "duration_minutes",
                    e.target.value === "" ? undefined : Number(e.target.value),
                  )
                }
                placeholder="Ej. 18"
              />
            </div>
          </div>

          {/* Biological + Chemical indicators */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-bio">Indicador biológico</Label>
              <Input
                id="st-bio"
                value={form.biological_indicator ?? ""}
                onChange={(e) =>
                  handleChange("biological_indicator", e.target.value)
                }
                placeholder="Ej. Negativo"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="st-chem">Indicador químico</Label>
              <Input
                id="st-chem"
                value={form.chemical_indicator ?? ""}
                onChange={(e) =>
                  handleChange("chemical_indicator", e.target.value)
                }
                placeholder="Ej. Viraje completo"
              />
            </div>
          </div>

          {/* Instrument IDs */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="st-instruments">
              IDs de instrumentos{" "}
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                (separados por coma)
              </span>
            </Label>
            <Input
              id="st-instruments"
              value={instrumentIdsRaw}
              onChange={(e) => setInstrumentIdsRaw(e.target.value)}
              placeholder="uuid-1, uuid-2, uuid-3"
            />
          </div>

          {/* Compliance */}
          <div className="flex items-center gap-2">
            <input
              id="st-compliant"
              type="checkbox"
              checked={form.is_compliant}
              onChange={(e) => handleChange("is_compliant", e.target.checked)}
              className="h-4 w-4 rounded border-[hsl(var(--border))] accent-primary-600 cursor-pointer"
            />
            <Label htmlFor="st-compliant" className="cursor-pointer text-sm">
              Ciclo cumple con los parámetros requeridos
            </Label>
          </div>

          {/* Signature data */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="st-signature">
              Firma digital{" "}
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                (datos base64)
              </span>
            </Label>
            <Input
              id="st-signature"
              value={form.signature_data ?? ""}
              onChange={(e) => handleChange("signature_data", e.target.value)}
              placeholder="data:image/png;base64,..."
            />
          </div>

          {/* Notes */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="st-notes">Observaciones</Label>
            <textarea
              id="st-notes"
              value={form.notes ?? ""}
              onChange={(e) => handleChange("notes", e.target.value)}
              placeholder="Observaciones adicionales..."
              rows={2}
              className={cn(
                "flex w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                "px-3 py-2 text-sm placeholder:text-[hsl(var(--muted-foreground))]",
                "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                "resize-none",
              )}
            />
          </div>

          <DialogFooter className="mt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={
                createMutation.isPending ||
                !form.autoclave_id.trim() ||
                !form.load_number.trim() ||
                !form.date ||
                !form.responsible_user_id.trim()
              }
            >
              {createMutation.isPending ? "Guardando..." : "Crear registro"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SterilizationPage() {
  const [page, setPage] = React.useState(1);
  const [showCreateDialog, setShowCreateDialog] = React.useState(false);

  const { data, isLoading } = useSterilizationRecords(page, 20);

  const records = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / (data?.page_size ?? 20));

  return (
    <div className="flex flex-col gap-6">
      {/* ─── Header with action button ──────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {total > 0
            ? `${total} ${total === 1 ? "registro" : "registros"} de esterilización`
            : "Sin registros"}
        </p>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo registro
        </Button>
      </div>

      {/* ─── Table ──────────────────────────────────────────────────────── */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
            </div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-20 text-[hsl(var(--muted-foreground))]">
              <FlaskConical className="h-10 w-10 opacity-40" />
              <p className="text-sm">No hay registros de esterilización.</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCreateDialog(true)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Crear primer registro
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Autoclave</TableHead>
                  <TableHead>N° de carga</TableHead>
                  <TableHead>Temperatura</TableHead>
                  <TableHead>Duración</TableHead>
                  <TableHead>Cumplimiento</TableHead>
                  <TableHead>Instrumentos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((record) => (
                  <TableRow key={record.id}>
                    <TableCell className="text-sm">
                      {new Date(record.date).toLocaleDateString("es-CO")}
                    </TableCell>
                    <TableCell className="font-medium text-foreground">
                      {record.autoclave_id}
                    </TableCell>
                    <TableCell className="text-sm">
                      {record.load_number}
                    </TableCell>
                    <TableCell className="text-sm tabular-nums">
                      {record.temperature_celsius !== null
                        ? `${record.temperature_celsius} °C`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-sm tabular-nums">
                      {record.duration_minutes !== null
                        ? `${record.duration_minutes} min`
                        : "—"}
                    </TableCell>
                    <TableCell>
                      {record.is_compliant ? (
                        <span className="flex items-center gap-1.5 text-green-600 text-sm font-medium">
                          <CheckCircle2 className="h-4 w-4" />
                          Cumple
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-[#ef4444] text-sm font-medium">
                          <XCircle className="h-4 w-4" />
                          No cumple
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm tabular-nums text-[hsl(var(--muted-foreground))]">
                      {record.instrument_ids.length > 0
                        ? `${record.instrument_ids.length} instrumento${record.instrument_ids.length !== 1 ? "s" : ""}`
                        : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ─── Pagination ─────────────────────────────────────────────────── */}
      {total > 0 && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            Anterior
          </Button>
          <span className="text-sm text-[hsl(var(--muted-foreground))]">
            Página {page} de {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
          >
            Siguiente
          </Button>
        </div>
      )}

      {/* ─── Create dialog ──────────────────────────────────────────────── */}
      <CreateSterilizationDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />
    </div>
  );
}
