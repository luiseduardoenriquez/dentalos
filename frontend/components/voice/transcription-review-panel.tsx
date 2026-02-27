"use client";

import * as React from "react";
import {
  Check,
  X,
  Edit,
  Trash2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useApplyFindings, type VoiceFinding, type ApplyResponse } from "@/lib/hooks/use-voice";
import { cn, truncate } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Confidence threshold below which findings are deselected by default */
const AUTO_SELECT_THRESHOLD = 0.7;

/** Human-readable zone translations (Spanish) */
const ZONE_LABELS: Record<string, string> = {
  mesial: "Mesial",
  distal: "Distal",
  oclusal: "Oclusal",
  vestibular: "Vestibular",
  lingual: "Lingual",
  cervical: "Cervical",
};

// ─── Types ────────────────────────────────────────────────────────────────────

interface TranscriptionReviewPanelProps {
  /** Parsed dental findings from the voice session */
  findings: VoiceFinding[];
  /** Warnings from the parse response */
  warnings: string[];
  /** Non-dental speech fragments that were filtered out */
  filteredSpeech: Record<string, unknown>[];
  /** Active voice session ID */
  sessionId: string;
  /** Callback fired after findings are successfully applied */
  onApplyComplete?: (result: ApplyResponse) => void;
  /** Callback fired when the user cancels the review */
  onCancel?: () => void;
  /** Compact mode for sidebar rendering — uses card list instead of table */
  compact?: boolean;
}

interface EditingState {
  index: number;
  tooth_number: number;
  zone: string;
  condition_code: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Returns Tailwind color classes based on confidence level */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "text-green-700 dark:text-green-400";
  if (confidence >= 0.7) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

/** Returns badge variant based on confidence level */
function getConfidenceBadgeVariant(confidence: number) {
  if (confidence >= 0.9) return "success" as const;
  if (confidence >= 0.7) return "warning" as const;
  return "destructive" as const;
}

/** Translates a zone string to Spanish, or returns "Diente completo" for empty */
function translateZone(zone: string): string {
  if (!zone) return "Diente completo";
  return ZONE_LABELS[zone] ?? zone;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Review panel for parsed dental findings from a voice session.
 * Allows the doctor to inspect, edit, select/deselect, and apply findings to the odontogram.
 */
export function TranscriptionReviewPanel({
  findings: initialFindings,
  warnings,
  filteredSpeech,
  sessionId,
  onApplyComplete,
  onCancel,
  compact = false,
}: TranscriptionReviewPanelProps) {
  // ─── State ──────────────────────────────────────────────────────────────────
  const [findings, setFindings] = React.useState<VoiceFinding[]>(initialFindings);
  const [selectedIndices, setSelectedIndices] = React.useState<Set<number>>(() => {
    const initial = new Set<number>();
    initialFindings.forEach((f, i) => {
      if (f.confidence >= AUTO_SELECT_THRESHOLD) initial.add(i);
    });
    return initial;
  });
  const [editing, setEditing] = React.useState<EditingState | null>(null);
  const [showFilteredSpeech, setShowFilteredSpeech] = React.useState(false);
  const [applyResult, setApplyResult] = React.useState<ApplyResponse | null>(null);
  const [confirmDeleteIndex, setConfirmDeleteIndex] = React.useState<number | null>(null);

  // ─── Hooks ──────────────────────────────────────────────────────────────────
  const { mutate: applyFindings, isPending: isApplying } = useApplyFindings();

  // ─── Sync findings when props change ────────────────────────────────────────
  React.useEffect(() => {
    setFindings(initialFindings);
    const initial = new Set<number>();
    initialFindings.forEach((f, i) => {
      if (f.confidence >= AUTO_SELECT_THRESHOLD) initial.add(i);
    });
    setSelectedIndices(initial);
    setApplyResult(null);
  }, [initialFindings]);

  // ─── Selection handlers ─────────────────────────────────────────────────────

  function toggleSelection(index: number) {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  function selectAll() {
    setSelectedIndices(new Set(findings.map((_, i) => i)));
  }

  function deselectAll() {
    setSelectedIndices(new Set());
  }

  const allSelected = selectedIndices.size === findings.length && findings.length > 0;

  // ─── Edit handlers ─────────────────────────────────────────────────────────

  function startEditing(index: number) {
    const finding = findings[index];
    setEditing({
      index,
      tooth_number: finding.tooth_number,
      zone: finding.zone,
      condition_code: finding.condition_code,
    });
  }

  function confirmEdit() {
    if (!editing) return;
    setFindings((prev) =>
      prev.map((f, i) =>
        i === editing.index
          ? { ...f, tooth_number: editing.tooth_number, zone: editing.zone, condition_code: editing.condition_code }
          : f,
      ),
    );
    setEditing(null);
  }

  function cancelEdit() {
    setEditing(null);
  }

  // ─── Delete handler ─────────────────────────────────────────────────────────

  function deleteFinding(index: number) {
    setFindings((prev) => prev.filter((_, i) => i !== index));
    setSelectedIndices((prev) => {
      const next = new Set<number>();
      prev.forEach((i) => {
        if (i < index) next.add(i);
        else if (i > index) next.add(i - 1);
        // Skip the deleted index
      });
      return next;
    });
    setConfirmDeleteIndex(null);
  }

  // ─── Apply handler ─────────────────────────────────────────────────────────

  function handleApply() {
    const selectedFindings = findings.filter((_, i) => selectedIndices.has(i));
    if (selectedFindings.length === 0) return;

    applyFindings(
      { sessionId, findings: selectedFindings },
      {
        onSuccess: (result) => {
          setApplyResult(result);
          onApplyComplete?.(result);
        },
      },
    );
  }

  // ─── Render: Apply result summary ───────────────────────────────────────────

  if (applyResult) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Check className="h-5 w-5 text-green-600" />
            Hallazgos aplicados
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-green-50 p-4 text-center dark:bg-green-900/20">
              <p className="text-2xl font-bold text-green-700 dark:text-green-400">
                {applyResult.applied_count}
              </p>
              <p className="text-sm text-green-600 dark:text-green-500">Aplicados</p>
            </div>
            <div className="rounded-lg bg-yellow-50 p-4 text-center dark:bg-yellow-900/20">
              <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-400">
                {applyResult.skipped_count}
              </p>
              <p className="text-sm text-yellow-600 dark:text-yellow-500">Omitidos</p>
            </div>
          </div>

          {/* Errors list */}
          {applyResult.errors.length > 0 && (
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">Errores:</p>
              <ul className="space-y-1">
                {applyResult.errors.map((err, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <Badge variant="destructive" className="text-xs">Error</Badge>
                    <span className="text-[hsl(var(--muted-foreground))]">{err}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // ─── Render: Main review panel ──────────────────────────────────────────────

  return (
    <Card>
      <CardHeader>
        <CardTitle>Revision de hallazgos</CardTitle>
        {/* Summary bar */}
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {findings.length} hallazgo{findings.length !== 1 ? "s" : ""} encontrado
          {findings.length !== 1 ? "s" : ""}, {selectedIndices.size} seleccionado
          {selectedIndices.size !== 1 ? "s" : ""} para aplicar
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Warnings section */}
        {warnings.length > 0 && (
          <div className="rounded-md border border-yellow-300 bg-yellow-50 p-3 dark:border-yellow-700 dark:bg-yellow-900/20">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-yellow-600 dark:text-yellow-400" />
              <div className="space-y-1">
                {warnings.map((warning, i) => (
                  <p key={i} className="text-sm text-yellow-800 dark:text-yellow-300">
                    {warning}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Findings */}
        {findings.length === 0 ? (
          <p className="py-8 text-center text-sm text-[hsl(var(--muted-foreground))]">
            No se encontraron hallazgos clinicos en la transcripcion.
          </p>
        ) : compact ? (
          /* Compact card list for sidebar */
          <div className="space-y-2 max-h-[40vh] overflow-y-auto">
            {findings.map((finding, index) => (
              <div
                key={index}
                className={cn(
                  "flex items-start gap-2 rounded-lg border p-2 text-sm transition-colors",
                  selectedIndices.has(index)
                    ? "border-primary-300 bg-primary-50/50 dark:border-primary-700 dark:bg-primary-900/10"
                    : "border-[hsl(var(--border))]",
                )}
              >
                <Checkbox
                  checked={selectedIndices.has(index)}
                  onCheckedChange={() => toggleSelection(index)}
                  className="mt-0.5"
                  aria-label={`Seleccionar hallazgo diente ${finding.tooth_number}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-medium">{finding.tooth_number}</span>
                    <span className="text-[hsl(var(--muted-foreground))]">&middot;</span>
                    <span className="capitalize">{finding.condition_code}</span>
                    <Badge variant={getConfidenceBadgeVariant(finding.confidence)} className="ml-auto text-[10px] px-1 py-0">
                      {Math.round(finding.confidence * 100)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    {translateZone(finding.zone)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))]">
                  <th className="w-10 p-2 text-left">
                    <Checkbox
                      checked={allSelected}
                      onCheckedChange={() => (allSelected ? deselectAll() : selectAll())}
                      aria-label="Seleccionar todos"
                    />
                  </th>
                  <th className="p-2 text-left font-medium text-[hsl(var(--muted-foreground))]">
                    Diente
                  </th>
                  <th className="p-2 text-left font-medium text-[hsl(var(--muted-foreground))]">
                    Zona
                  </th>
                  <th className="p-2 text-left font-medium text-[hsl(var(--muted-foreground))]">
                    Hallazgo
                  </th>
                  <th className="p-2 text-left font-medium text-[hsl(var(--muted-foreground))]">
                    Confianza
                  </th>
                  <th className="p-2 text-left font-medium text-[hsl(var(--muted-foreground))]">
                    Texto original
                  </th>
                  <th className="w-20 p-2 text-right font-medium text-[hsl(var(--muted-foreground))]">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody>
                {findings.map((finding, index) => {
                  const isEditing = editing?.index === index;
                  const isConfirmingDelete = confirmDeleteIndex === index;

                  return (
                    <tr
                      key={index}
                      className={cn(
                        "border-b border-[hsl(var(--border))] transition-colors",
                        selectedIndices.has(index) && "bg-primary-50/50 dark:bg-primary-900/10",
                        isConfirmingDelete && "bg-red-50/50 dark:bg-red-900/10",
                      )}
                    >
                      {/* Selection checkbox */}
                      <td className="p-2">
                        <Checkbox
                          checked={selectedIndices.has(index)}
                          onCheckedChange={() => toggleSelection(index)}
                          aria-label={`Seleccionar hallazgo diente ${finding.tooth_number}`}
                        />
                      </td>

                      {/* Tooth number */}
                      <td className="p-2 font-mono">
                        {isEditing ? (
                          <input
                            type="number"
                            min={11}
                            max={85}
                            value={editing.tooth_number}
                            onChange={(e) =>
                              setEditing({ ...editing, tooth_number: parseInt(e.target.value, 10) || 0 })
                            }
                            className="w-16 rounded border border-[hsl(var(--border))] bg-transparent px-2 py-1 text-sm"
                          />
                        ) : (
                          finding.tooth_number
                        )}
                      </td>

                      {/* Zone */}
                      <td className="p-2">
                        {isEditing ? (
                          <select
                            value={editing.zone ?? ""}
                            onChange={(e) =>
                              setEditing({ ...editing, zone: e.target.value })
                            }
                            className="rounded border border-[hsl(var(--border))] bg-transparent px-2 py-1 text-sm"
                          >
                            <option value="">Diente completo</option>
                            <option value="mesial">Mesial</option>
                            <option value="distal">Distal</option>
                            <option value="oclusal">Oclusal</option>
                            <option value="vestibular">Vestibular</option>
                            <option value="lingual">Lingual</option>
                            <option value="cervical">Cervical</option>
                          </select>
                        ) : (
                          translateZone(finding.zone)
                        )}
                      </td>

                      {/* Condition */}
                      <td className="p-2">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editing.condition_code}
                            onChange={(e) =>
                              setEditing({ ...editing, condition_code: e.target.value })
                            }
                            className="w-32 rounded border border-[hsl(var(--border))] bg-transparent px-2 py-1 text-sm"
                          />
                        ) : (
                          <span className="capitalize">{finding.condition_code}</span>
                        )}
                      </td>

                      {/* Confidence */}
                      <td className="p-2">
                        <Badge variant={getConfidenceBadgeVariant(finding.confidence)}>
                          <span className={cn("font-mono", getConfidenceColor(finding.confidence))}>
                            {Math.round(finding.confidence * 100)}%
                          </span>
                        </Badge>
                      </td>

                      {/* Source text */}
                      <td className="p-2 max-w-[200px]">
                        <span
                          className="text-xs text-[hsl(var(--muted-foreground))] italic"
                          title={finding.source_text ?? ""}
                        >
                          {truncate(finding.source_text ?? "", 50)}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="p-2 text-right">
                        {isEditing ? (
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={confirmEdit}
                              title="Confirmar edicion"
                            >
                              <Check className="h-4 w-4 text-green-600" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={cancelEdit}
                              title="Cancelar edicion"
                            >
                              <X className="h-4 w-4 text-red-600" />
                            </Button>
                          </div>
                        ) : isConfirmingDelete ? (
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => deleteFinding(index)}
                              title="Confirmar eliminacion"
                            >
                              <Check className="h-4 w-4 text-red-600" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => setConfirmDeleteIndex(null)}
                              title="Cancelar eliminacion"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => startEditing(index)}
                              title="Editar hallazgo"
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => setConfirmDeleteIndex(index)}
                              title="Eliminar hallazgo"
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Filtered speech section (collapsible) */}
        {filteredSpeech.length > 0 && (
          <div className="rounded-md border border-[hsl(var(--border))]">
            <button
              onClick={() => setShowFilteredSpeech(!showFilteredSpeech)}
              className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] transition-colors rounded-md"
            >
              <span>Texto filtrado ({filteredSpeech.length} fragmento{filteredSpeech.length !== 1 ? "s" : ""})</span>
              {showFilteredSpeech ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
            {showFilteredSpeech && (
              <div className="border-t border-[hsl(var(--border))] px-4 py-3 space-y-1">
                {filteredSpeech.map((entry, i) => {
                  const text = (entry.text as string) ?? JSON.stringify(entry);
                  return (
                    <p key={i} className="text-xs text-[hsl(var(--muted-foreground))] italic">
                      &quot;{text}&quot;
                    </p>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Bottom action bar */}
        {findings.length > 0 && (
          <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center sm:justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={allSelected ? deselectAll : selectAll}
            >
              {allSelected ? "Deseleccionar" : "Seleccionar todos"}
            </Button>

            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={onCancel}>
                Cancelar
              </Button>
              <Button
                onClick={handleApply}
                disabled={selectedIndices.size === 0 || isApplying}
              >
                {isApplying && <Loader2 className="h-4 w-4 animate-spin" />}
                {compact ? `Aplicar (${selectedIndices.size})` : `Aplicar al odontograma (${selectedIndices.size})`}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
