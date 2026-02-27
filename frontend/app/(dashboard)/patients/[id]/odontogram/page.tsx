"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight, AlertCircle, Lock } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/empty-state";

import { ToothGrid } from "@/components/odontogram/tooth-grid";
import { ConditionPanel } from "@/components/odontogram/condition-panel";
import { HistoryPanel } from "@/components/odontogram/history-panel";
import { ToothDetailPanel } from "@/components/odontogram/tooth-detail-panel";
import { OdontogramToolbar } from "@/components/odontogram/odontogram-toolbar";

import { VoiceContextualPanel } from "@/components/voice/voice-contextual-panel";
import { useVoiceStore } from "@/lib/stores/voice-store";
import { useVoiceNavigationGuard } from "@/lib/hooks/use-voice-navigation-guard";

import {
  useOdontogram,
  useConditionsCatalog,
  useUpdateCondition,
  useCreateSnapshot,
  useToggleDentition,
} from "@/lib/hooks/use-odontogram";
import { usePatient } from "@/lib/hooks/use-patients";
import { useAuth } from "@/lib/hooks/use-auth";

import type { DentitionType, ConditionCreateValues } from "@/lib/validations/odontogram";

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function OdontogramSkeleton() {
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
      </div>
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-9 w-64 rounded-lg" />
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24 rounded-md" />
          <Skeleton className="h-9 w-24 rounded-md" />
        </div>
      </div>
      {/* Grid area */}
      <div className="flex gap-4">
        <Skeleton className="h-[400px] flex-1 rounded-xl" />
        <Skeleton className="h-[400px] w-72 rounded-xl" />
      </div>
      {/* Status bar */}
      <Skeleton className="h-8 w-full rounded-md" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OdontogramPage() {
  const params = useParams<{ id: string }>();
  const patientId = params.id;

  // ── Auth ──────────────────────────────────────────────────────────
  const { has_permission } = useAuth();
  const canWrite = has_permission("odontogram:write");

  // ── Data hooks ────────────────────────────────────────────────────
  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: odontogram, isLoading: isLoadingOdontogram } =
    useOdontogram(patientId);
  const { data: catalog } = useConditionsCatalog();

  // ── Voice ─────────────────────────────────────────────────────────
  const [voiceActive, setVoiceActive] = React.useState(false);
  const voiceStore = useVoiceStore();
  useVoiceNavigationGuard();

  const handleVoiceStart = React.useCallback(() => {
    if (voiceStore.phase !== "idle" && voiceStore.phase !== "success") return;
    voiceStore.start_contextual(patientId, patient?.full_name ?? "");
    setVoiceActive(true);
  }, [voiceStore, patientId, patient?.full_name]);

  const handleVoiceClose = React.useCallback(() => {
    setVoiceActive(false);
    voiceStore.reset();
  }, [voiceStore]);

  // ── Mutations ─────────────────────────────────────────────────────
  const { mutate: updateCondition, isPending: isUpdating } =
    useUpdateCondition();
  const { mutate: createSnapshot, isPending: isSnapshotting } =
    useCreateSnapshot();
  const { mutate: toggleDentition, isPending: isTogglingDentition } =
    useToggleDentition();

  // ── Local state ───────────────────────────────────────────────────
  const [selectedTooth, setSelectedTooth] = React.useState<number | null>(null);
  const [selectedZone, setSelectedZone] = React.useState<string | null>(null);
  const [selectedCondition, setSelectedCondition] = React.useState<
    string | null
  >(null);
  const [severity, setSeverity] = React.useState<string | null>(null);
  const [notes, setNotes] = React.useState("");
  const [showHistory, setShowHistory] = React.useState(false);
  const [showToothDetail, setShowToothDetail] = React.useState(false);
  const [historyToothFilter, setHistoryToothFilter] = React.useState<
    number | undefined
  >(undefined);

  // ── Derived state ─────────────────────────────────────────────────
  const dentitionType: DentitionType =
    (odontogram?.dentition_type as DentitionType) ?? "adult";
  const isLoading = isLoadingPatient || isLoadingOdontogram;
  const isMutating = isUpdating || isSnapshotting || isTogglingDentition;
  const hasSelection = selectedTooth !== null && selectedZone !== null;

  // ── Callbacks ─────────────────────────────────────────────────────

  const handleZoneClick = React.useCallback(
    (toothNumber: number, zone: string) => {
      if (selectedTooth === toothNumber && selectedZone === zone) {
        // Clicking the same zone deselects it
        setSelectedZone(null);
      } else {
        setSelectedTooth(toothNumber);
        setSelectedZone(zone);
      }
      // Reset condition selection when changing zone
      setSelectedCondition(null);
      setSeverity(null);
      setNotes("");
      // Close tooth detail if open
      setShowToothDetail(false);
    },
    [selectedTooth, selectedZone],
  );

  const handleToothClick = React.useCallback(
    (toothNumber: number) => {
      if (selectedTooth === toothNumber) {
        // Toggle tooth detail panel
        setShowToothDetail((prev) => !prev);
      } else {
        setSelectedTooth(toothNumber);
        setSelectedZone(null);
        setShowToothDetail(true);
      }
      // Reset condition selection
      setSelectedCondition(null);
      setSeverity(null);
      setNotes("");
    },
    [selectedTooth],
  );

  const handleConditionSelect = React.useCallback(
    (conditionCode: string) => {
      setSelectedCondition(
        selectedCondition === conditionCode ? null : conditionCode,
      );
      setSeverity(null);
    },
    [selectedCondition],
  );

  const handleApply = React.useCallback(() => {
    if (!selectedTooth || !selectedZone || !selectedCondition) return;

    updateCondition(
      {
        patientId,
        data: {
          tooth_number: selectedTooth,
          zone: selectedZone as ConditionCreateValues["zone"],
          condition_code: selectedCondition as ConditionCreateValues["condition_code"],
          severity: (severity as ConditionCreateValues["severity"]) ?? null,
          notes: notes.trim() || null,
          source: "manual",
        },
      },
      {
        onSuccess: () => {
          // Clear selection after successful apply
          setSelectedCondition(null);
          setSeverity(null);
          setNotes("");
        },
      },
    );
  }, [
    patientId,
    selectedTooth,
    selectedZone,
    selectedCondition,
    severity,
    notes,
    updateCondition,
  ]);

  const handleDentitionChange = React.useCallback(
    (type: DentitionType) => {
      if (type === dentitionType) return;
      toggleDentition({
        patientId,
        data: { dentition_type: type },
      });
      // Clear selection when changing dentition
      setSelectedTooth(null);
      setSelectedZone(null);
      setSelectedCondition(null);
    },
    [patientId, dentitionType, toggleDentition],
  );

  const handleSnapshotCreate = React.useCallback(() => {
    createSnapshot({
      patientId,
      data: { label: null },
    });
  }, [patientId, createSnapshot]);

  const handleHistoryOpen = React.useCallback(() => {
    setHistoryToothFilter(undefined);
    setShowHistory(true);
    setShowToothDetail(false);
  }, []);

  const handleOpenToothHistory = React.useCallback((toothNumber: number) => {
    setHistoryToothFilter(toothNumber);
    setShowHistory(true);
    setShowToothDetail(false);
  }, []);

  // ── Loading State ─────────────────────────────────────────────────

  if (isLoading) {
    return <OdontogramSkeleton />;
  }

  if (!patient) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Paciente no encontrado"
        description="El paciente que buscas no existe o no tienes permiso para verlo."
        action={{ label: "Volver a pacientes", href: "/patients" }}
      />
    );
  }

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* ─── Breadcrumb ──────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegacion"
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
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {patient.full_name}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Odontograma</span>
      </nav>

      {/* ─── Read-only Banner ────────────────────────────────────────── */}
      {!canWrite && (
        <div className="flex items-center gap-2 rounded-md border border-warning-300 bg-warning-50 px-4 py-2 text-sm text-warning-700 dark:border-warning-700 dark:bg-warning-900/20 dark:text-warning-300">
          <Lock className="h-4 w-4 shrink-0" />
          <span>
            Modo de solo lectura. No tienes permiso para editar el odontograma.
          </span>
        </div>
      )}

      {/* ─── Toolbar ─────────────────────────────────────────────────── */}
      <OdontogramToolbar
        dentitionType={dentitionType}
        onDentitionChange={handleDentitionChange}
        onSnapshotCreate={handleSnapshotCreate}
        onHistoryOpen={handleHistoryOpen}
        onVoiceStart={handleVoiceStart}
        isVoiceActive={voiceActive}
        isLoading={isMutating}
        readOnly={!canWrite}
      />

      {/* ─── Main Content ────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 lg:flex-row">
        {/* Tooth Grid (main area) */}
        <Card className="flex-1 overflow-hidden">
          <CardContent className="p-0">
            <ToothGrid
              teeth={odontogram?.teeth ?? []}
              dentitionType={dentitionType}
              selectedTooth={selectedTooth}
              selectedZone={selectedZone}
              onZoneClick={handleZoneClick}
              onToothClick={handleToothClick}
              readOnly={!canWrite}
            />
          </CardContent>
        </Card>

        {/* Sidebar: Condition Panel / Tooth Detail / History */}
        <div className="w-full lg:w-80 shrink-0 space-y-4">
          {/* Voice Panel (takes precedence when active) */}
          {voiceActive && (
            <VoiceContextualPanel
              patient_id={patientId}
              patient_name={patient?.full_name ?? ""}
              onClose={handleVoiceClose}
            />
          )}

          {/* History Panel (takes precedence when open, hidden during voice) */}
          {showHistory && !voiceActive && (
            <HistoryPanel
              patientId={patientId}
              toothNumber={historyToothFilter}
              isOpen={showHistory}
              onClose={() => setShowHistory(false)}
            />
          )}

          {/* Tooth Detail Panel */}
          {showToothDetail && selectedTooth && !showHistory && !voiceActive && (
            <ToothDetailPanel
              patientId={patientId}
              toothNumber={selectedTooth}
              onClose={() => setShowToothDetail(false)}
              onOpenHistory={handleOpenToothHistory}
            />
          )}

          {/* Condition Panel (always visible when not read-only, hidden during voice) */}
          {canWrite && !showHistory && !voiceActive && (
            <ConditionPanel
              conditions={catalog ?? []}
              selectedCondition={selectedCondition}
              onConditionSelect={handleConditionSelect}
              selectedZone={selectedZone}
              severity={severity}
              onSeverityChange={setSeverity}
              notes={notes}
              onNotesChange={setNotes}
              onApply={handleApply}
              isApplying={isUpdating}
              hasSelection={hasSelection}
            />
          )}
        </div>
      </div>

      {/* ─── Status Bar ──────────────────────────────────────────────── */}
      <Card>
        <CardContent className="py-2 px-4">
          <div className="flex flex-wrap items-center gap-4 text-xs text-[hsl(var(--muted-foreground))]">
            <span>
              <span className="font-medium text-foreground">
                {odontogram?.total_conditions ?? 0}
              </span>{" "}
              condicion{(odontogram?.total_conditions ?? 0) !== 1 ? "es" : ""}
            </span>

            {odontogram?.last_updated && (
              <>
                <span className="hidden sm:inline">&mdash;</span>
                <span>
                  Ultima actualizacion:{" "}
                  <span className="font-medium text-foreground">
                    {formatDateTime(odontogram.last_updated)}
                  </span>
                </span>
              </>
            )}

            {selectedTooth && (
              <>
                <span className="hidden sm:inline">&mdash;</span>
                <span>
                  Diente seleccionado:{" "}
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                    {selectedTooth}
                  </Badge>
                  {selectedZone && (
                    <span className="ml-1 font-medium text-foreground">
                      ({selectedZone})
                    </span>
                  )}
                </span>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
