"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ChevronRight } from "lucide-react";
import {
  ADULT_TEETH,
  PEDIATRIC_TEETH,
  DENTITION_LABELS,
} from "@/lib/validations/odontogram";
import type { DentitionType } from "@/lib/validations/odontogram";
import {
  PerioMeasurementGrid,
} from "@/components/perio-measurement-grid";
import type {
  PerioToothRow,
  PerioSite,
  PerioMeasurementCell,
} from "@/components/perio-measurement-grid";
import { useCreatePeriodontalRecord } from "@/lib/hooks/use-periodontal";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Site key mapping (short → API) ──────────────────────────────────────────

const SITE_TO_API: Record<string, string> = {
  mb: "mesial_buccal",
  b: "buccal",
  db: "distal_buccal",
  ml: "mesial_lingual",
  l: "lingual",
  dl: "distal_lingual",
};

const SITES: PerioSite[] = ["mb", "b", "db", "ml", "l", "dl"];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function buildTeeth(type: DentitionType): PerioToothRow[] {
  let toothNumbers: readonly number[];
  if (type === "adult") toothNumbers = ADULT_TEETH;
  else if (type === "pediatric") toothNumbers = PEDIATRIC_TEETH;
  else toothNumbers = [...ADULT_TEETH, ...PEDIATRIC_TEETH];

  return toothNumbers.map((num) => ({
    tooth_number: String(num),
    measurements: SITES.map<PerioMeasurementCell>((site) => ({
      site,
      pocket_depth: 0,
      bleeding: false,
    })),
  }));
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function NewPeriodontalRecordPage() {
  const params = useParams<{ id: string }>();
  const patientId = params?.id ?? "";
  const router = useRouter();
  const { error: toastError } = useToast();

  const [dentitionType, setDentitionType] = React.useState<DentitionType>("adult");
  const [teeth, setTeeth] = React.useState<PerioToothRow[]>(() => buildTeeth("adult"));
  const [notes, setNotes] = React.useState("");

  const { mutate: createRecord, isPending } = useCreatePeriodontalRecord(patientId);

  // Rebuild teeth when dentition type changes
  function handleDentitionChange(value: string) {
    const dt = value as DentitionType;
    setDentitionType(dt);
    setTeeth(buildTeeth(dt));
  }

  // Update pocket depth for a specific tooth/site
  const onCellChange = React.useCallback(
    (toothNumber: string, site: PerioSite, value: number) => {
      setTeeth((prev) =>
        prev.map((row) => {
          if (row.tooth_number !== toothNumber) return row;
          return {
            ...row,
            measurements: row.measurements.map((m) =>
              m.site === site ? { ...m, pocket_depth: value } : m,
            ),
          };
        }),
      );
    },
    [],
  );

  // Toggle bleeding for a specific tooth/site
  const onBleedingChange = React.useCallback(
    (toothNumber: string, site: PerioSite, bleeding: boolean) => {
      setTeeth((prev) =>
        prev.map((row) => {
          if (row.tooth_number !== toothNumber) return row;
          return {
            ...row,
            measurements: row.measurements.map((m) =>
              m.site === site ? { ...m, bleeding } : m,
            ),
          };
        }),
      );
    },
    [],
  );

  function handleSubmit() {
    // Flatten teeth → measurements where pocket_depth > 0
    const measurements = teeth.flatMap((row) =>
      row.measurements
        .filter((m) => m.pocket_depth > 0)
        .map((m) => ({
          tooth_number: parseInt(row.tooth_number, 10),
          site: SITE_TO_API[m.site],
          pocket_depth: m.pocket_depth,
          bleeding_on_probing: m.bleeding,
        })),
    );

    if (measurements.length === 0) {
      toastError(
        "Sin mediciones",
        "Ingresa al menos una medición de profundidad de bolsa antes de guardar.",
      );
      return;
    }

    createRecord(
      {
        dentition_type: dentitionType,
        source: "manual",
        notes: notes.trim() || null,
        measurements,
      },
      {
        onSuccess: () => {
          router.push(`/patients/${patientId}/periodontal`);
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}`}
          className="hover:text-foreground transition-colors"
        >
          Paciente
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patientId}/periodontal`}
          className="hover:text-foreground transition-colors"
        >
          Periodontograma
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Nuevo registro</span>
      </nav>

      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Nuevo registro periodontal
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Registra las mediciones de profundidad de bolsa y sangrado al sondaje.
        </p>
      </div>

      {/* ─── Card 1: Configuración ───────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuración</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="dentition-type">Tipo de dentición</Label>
              <Select value={dentitionType} onValueChange={handleDentitionChange}>
                <SelectTrigger id="dentition-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.entries(DENTITION_LABELS) as [DentitionType, string][]).map(
                    ([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="notes">Notas (opcional)</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Observaciones generales del periodontograma..."
              maxLength={2000}
              rows={3}
            />
          </div>
        </CardContent>
      </Card>

      {/* ─── Card 2: Mediciones ──────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mediciones</CardTitle>
        </CardHeader>
        <CardContent>
          <PerioMeasurementGrid
            teeth={teeth}
            editable
            onCellChange={onCellChange}
            onBleedingChange={onBleedingChange}
          />
        </CardContent>
      </Card>

      {/* ─── Footer ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-end gap-3">
        <Button variant="outline" asChild>
          <Link href={`/patients/${patientId}/periodontal`}>Cancelar</Link>
        </Button>
        <Button onClick={handleSubmit} disabled={isPending}>
          {isPending ? "Creando..." : "Crear registro"}
        </Button>
      </div>
    </div>
  );
}
