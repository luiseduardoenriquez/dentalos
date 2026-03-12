"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, ChevronRight, Clipboard, AlertCircle } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types (aligned with backend schemas/periodontal.py) ─────────────────────

interface PeriodontalMeasurement {
  id: string;
  tooth_number: number;
  site: string; // mesial_buccal | buccal | distal_buccal | mesial_lingual | lingual | distal_lingual
  pocket_depth: number | null;
  recession: number | null;
  clinical_attachment_level: number | null;
  bleeding_on_probing: boolean | null;
  plaque_index: boolean | null;
  mobility: number | null;
  furcation: number | null;
}

/** List item — no measurements, just metadata. */
interface PeriodontalListItem {
  id: string;
  recorded_by: string;
  dentition_type: string; // adult | pediatric | mixed
  source: string; // manual | voice
  measurement_count: number;
  created_at: string;
}

/** Full record with measurements (detail endpoint). */
interface PeriodontalRecord {
  id: string;
  patient_id: string;
  recorded_by: string;
  dentition_type: string;
  source: string;
  notes: string | null;
  measurements: PeriodontalMeasurement[];
  created_at: string;
  updated_at: string;
}

interface PeriodontalListResponse {
  items: PeriodontalListItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function depthColor(depth: number): string {
  if (depth <= 3) return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300";
  if (depth <= 5) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300";
  if (depth <= 7) return "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300";
  return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
}

const DENTITION_LABELS: Record<string, string> = {
  adult: "Permanente",
  pediatric: "Temporal",
  mixed: "Mixta",
};

const SITE_ORDER = [
  "mesial_buccal",
  "buccal",
  "distal_buccal",
  "mesial_lingual",
  "lingual",
  "distal_lingual",
] as const;

const SITE_SHORT_LABELS: Record<string, string> = {
  mesial_buccal: "MB",
  buccal: "B",
  distal_buccal: "DB",
  mesial_lingual: "ML",
  lingual: "L",
  distal_lingual: "DL",
};

// ─── Measurement Mini Grid ──────────────────────────────────────────────────

function MeasurementMiniGrid({
  measurements,
}: {
  measurements: PeriodontalMeasurement[];
}) {
  const byTooth = React.useMemo(() => {
    const map: Record<number, Record<string, PeriodontalMeasurement>> = {};
    for (const m of measurements) {
      if (!map[m.tooth_number]) map[m.tooth_number] = {};
      map[m.tooth_number][m.site] = m;
    }
    return map;
  }, [measurements]);

  const teeth = Object.keys(byTooth)
    .map(Number)
    .sort((a, b) => a - b);

  if (teeth.length === 0) {
    return (
      <p className="text-xs text-[hsl(var(--muted-foreground))] italic">
        Sin mediciones registradas.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="text-xs w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left px-2 py-1 text-[hsl(var(--muted-foreground))] w-12">
              Diente
            </th>
            {SITE_ORDER.map((s) => (
              <th
                key={s}
                className="text-center px-1 py-1 text-[hsl(var(--muted-foreground))] w-10"
              >
                {SITE_SHORT_LABELS[s]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teeth.slice(0, 8).map((tooth) => {
            const siteMap = byTooth[tooth];
            return (
              <tr key={tooth} className="border-t border-[hsl(var(--border))]">
                <td className="px-2 py-1 font-mono font-semibold text-foreground">
                  {tooth}
                </td>
                {SITE_ORDER.map((site) => {
                  const m = siteMap[site];
                  return (
                    <td key={site} className="px-1 py-1 text-center">
                      {m && m.pocket_depth != null ? (
                        <span
                          className={cn(
                            "inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold",
                            depthColor(m.pocket_depth),
                          )}
                        >
                          {m.pocket_depth}
                          {m.bleeding_on_probing && (
                            <span className="ml-0.5 h-1 w-1 rounded-full bg-red-500 inline-block" />
                          )}
                        </span>
                      ) : (
                        <span className="text-[hsl(var(--muted-foreground))]">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
          {teeth.length > 8 && (
            <tr>
              <td colSpan={7} className="px-2 py-1 text-[hsl(var(--muted-foreground))] text-center">
                +{teeth.length - 8} dientes más...
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ─── Expandable Record Row ──────────────────────────────────────────────────

function RecordRow({
  item,
  patientId,
  expanded,
  onToggle,
}: {
  item: PeriodontalListItem;
  patientId: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  // Fetch full detail (with measurements) only when expanded
  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["periodontal-record-detail", patientId, item.id],
    queryFn: () =>
      apiGet<PeriodontalRecord>(
        `/patients/${patientId}/periodontal-records/${item.id}`,
      ),
    enabled: expanded,
    staleTime: 60_000,
  });

  return (
    <div className="border border-[hsl(var(--border))] rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[hsl(var(--muted))]/50 transition-colors text-left"
      >
        <div className="flex items-center gap-4 min-w-0">
          <div className="shrink-0">
            <p className="text-sm font-semibold text-foreground">
              {formatDate(item.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="secondary">
              {DENTITION_LABELS[item.dentition_type] ?? item.dentition_type}
            </Badge>
            {item.source === "voice" ? (
              <Badge variant="default">Voz</Badge>
            ) : (
              <Badge variant="outline">Manual</Badge>
            )}
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              {item.measurement_count} mediciones
            </span>
          </div>
        </div>
        <ChevronRight
          className={cn(
            "h-4 w-4 text-[hsl(var(--muted-foreground))] transition-transform shrink-0",
            expanded && "rotate-90",
          )}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-[hsl(var(--border))] bg-[hsl(var(--muted))]/20">
          {detailLoading ? (
            <div className="space-y-2 py-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : detail ? (
            <>
              {/* Legend */}
              <div className="flex items-center gap-3 mb-3 flex-wrap">
                <span className="text-xs text-[hsl(var(--muted-foreground))]">Bolsa:</span>
                {[
                  { label: "1-3mm", color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300" },
                  { label: "4-5mm", color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300" },
                  { label: "6-7mm", color: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300" },
                  { label: "8+mm", color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300" },
                ].map((i) => (
                  <span
                    key={i.label}
                    className={cn("text-xs px-1.5 py-0.5 rounded font-medium", i.color)}
                  >
                    {i.label}
                  </span>
                ))}
                <span className="text-xs text-[hsl(var(--muted-foreground))] ml-1">
                  · Punto rojo = sangrado
                </span>
              </div>
              <MeasurementMiniGrid measurements={detail.measurements} />
              {detail.notes && (
                <p className="mt-3 text-xs text-[hsl(var(--muted-foreground))] border-t border-[hsl(var(--border))] pt-2">
                  <span className="font-medium text-foreground">Notas:</span> {detail.notes}
                </p>
              )}
            </>
          ) : (
            <p className="text-xs text-[hsl(var(--muted-foreground))] py-2">
              No se pudieron cargar los detalles.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function PeriodontalPage() {
  const params = useParams<{ id: string }>();
  const patientId = params?.id ?? "";
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["periodontal-records", patientId],
    queryFn: () =>
      apiGet<PeriodontalListResponse>(`/patients/${patientId}/periodontal-records`),
    enabled: !!patientId,
    staleTime: 30_000,
  });

  const records = data?.items ?? [];

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
        <span className="text-foreground font-medium">Periodontograma</span>
      </nav>

      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Periodontograma
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Registros de medición de bolsas periodontales y parámetros clínicos.
          </p>
        </div>
        <Button asChild>
          <Link href={`/patients/${patientId}/periodontal/new`}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo registro
          </Link>
        </Button>
      </div>

      {/* ─── Legend Card ─────────────────────────────────────────────────── */}
      <Card className="border-dashed">
        <CardContent className="py-3">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <span className="text-[hsl(var(--muted-foreground))] font-medium">
              Profundidad de bolsa:
            </span>
            <span className="px-2 py-0.5 rounded bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 font-medium">
              1–3 mm — Normal
            </span>
            <span className="px-2 py-0.5 rounded bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 font-medium">
              4–5 mm — Moderada
            </span>
            <span className="px-2 py-0.5 rounded bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 font-medium">
              6–7 mm — Severa
            </span>
            <span className="px-2 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 font-medium">
              8+ mm — Crítica
            </span>
          </div>
        </CardContent>
      </Card>

      {/* ─── Records List ────────────────────────────────────────────────── */}
      <div className="space-y-3">
        {isLoading ? (
          <>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </>
        ) : isError ? (
          <Card>
            <CardContent className="py-10">
              <div className="flex flex-col items-center gap-3 text-center">
                <AlertCircle className="h-8 w-8 text-red-500" />
                <p className="text-sm text-red-600 dark:text-red-400">
                  No se pudieron cargar los registros periodontales.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : records.length === 0 ? (
          <Card>
            <CardContent className="py-14">
              <div className="flex flex-col items-center gap-3 text-center">
                <Clipboard className="h-10 w-10 text-[hsl(var(--muted-foreground))]" />
                <p className="text-sm font-medium text-foreground">
                  Sin registros periodontales
                </p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Crea el primer registro de periodontograma para este paciente.
                </p>
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/patients/${patientId}/periodontal/new`}>
                    <Plus className="mr-2 h-3.5 w-3.5" />
                    Nuevo registro
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          records.map((record) => (
            <RecordRow
              key={record.id}
              item={record}
              patientId={patientId}
              expanded={expandedId === record.id}
              onToggle={() =>
                setExpandedId((prev) => (prev === record.id ? null : record.id))
              }
            />
          ))
        )}
      </div>

      {/* Summary footer */}
      {records.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Resumen</CardTitle>
            <CardDescription className="text-xs">
              {data?.total ?? records.length} registro{(data?.total ?? records.length) !== 1 ? "s" : ""} periodontales en total
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
