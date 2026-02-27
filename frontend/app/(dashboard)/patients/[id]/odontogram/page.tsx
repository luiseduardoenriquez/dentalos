"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight, AlertCircle, Lock, Monitor } from "lucide-react";

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
import type { ViewMode } from "@/components/odontogram/odontogram-toolbar";

// Lazy-loaded anatomic components — only bundled when anatomic view is active
const ToothArchSVG = React.lazy(() =>
  import("@/components/odontogram/anatomic/tooth-arch-svg").then((m) => ({
    default: m.ToothArchSVG,
  })),
);
const ToothDetailModal = React.lazy(() =>
  import("@/components/odontogram/anatomic/tooth-detail-modal").then((m) => ({
    default: m.ToothDetailModal,
  })),
);

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
import { useOdontogramSettings } from "@/lib/hooks/use-odontogram-settings";
import { usePlanLimits } from "@/lib/hooks/use-settings";

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

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Compute % of healthy teeth (all zones clear) */
function computeHealthyPercentage(
  teeth: { zones: { condition: unknown }[] }[],
): number {
  if (teeth.length === 0) return 100;
  const healthyCount = teeth.filter((t) =>
    t.zones.every((z) => z.condition === null || z.condition === undefined),
  ).length;
  return Math.round((healthyCount / teeth.length) * 100);
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

  // ── Settings & Plan ─────────────────────────────────────────────────
  const { data: odontogramSettings } = useOdontogramSettings();
  const { data: planLimits } = usePlanLimits();

  // Check if anatomic view is available for this plan
  const canUseAnatomic = planLimits?.features?.odontogram_anatomic === true;

  // Derive initial view mode from settings, gated by plan
  const defaultViewMode: ViewMode =
    canUseAnatomic && odontogramSettings?.default_view === "anatomic"
      ? "anatomic"
      : "classic";

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

  // ── View mode (session-level local state) ──────────────────────────
  const [viewMode, setViewMode] = React.useState<ViewMode>("classic");
  const [showAnatomicModal, setShowAnatomicModal] = React.useState(false);

  // Sync view mode from settings once loaded
  React.useEffect(() => {
    if (odontogramSettings && planLimits) {
      const mode: ViewMode =
        canUseAnatomic && odontogramSettings.default_view === "anatomic"
          ? "anatomic"
          : "classic";
      setViewMode(mode);
    }
  }, [odontogramSettings, planLimits, canUseAnatomic]);

  // ── Mobile detection (< 640px) for anatomic guard ──────────────────
  const [isMobile, setIsMobile] = React.useState(false);
  React.useEffect(() => {
    function checkMobile() {
      setIsMobile(window.innerWidth < 640);
    }
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // ── Derived state ─────────────────────────────────────────────────
  const dentitionType: DentitionType =
    (odontogram?.dentition_type as DentitionType) ?? "adult";
  const isLoading = isLoadingPatient || isLoadingOdontogram;
  const isMutating = isUpdating || isSnapshotting || isTogglingDentition;
  const hasSelection = selectedTooth !== null && selectedZone !== null;
  const isAnatomic = viewMode === "anatomic" && !isMobile;

  // Find tooth data for the selected tooth (used in anatomic modal)
  const selectedToothData = React.useMemo(() => {
    if (!selectedTooth || !odontogram?.teeth) return null;
    return odontogram.teeth.find((t) => t.tooth_number === selectedTooth) ?? null;
  }, [selectedTooth, odontogram?.teeth]);

  // ── Callbacks ─────────────────────────────────────────────────────

  const handleZoneClick = React.useCallback(
    (toothNumber: number, zone: string) => {
      if (selectedTooth === toothNumber && selectedZone === zone) {
        setSelectedZone(null);
      } else {
        setSelectedTooth(toothNumber);
        setSelectedZone(zone);
      }
      setSelectedCondition(null);
      setSeverity(null);
      setNotes("");
      setShowToothDetail(false);
    },
    [selectedTooth, selectedZone],
  );

  const handleToothClick = React.useCallback(
    (toothNumber: number) => {
      if (isAnatomic) {
        // In anatomic view, clicking a tooth opens the detail modal
        setSelectedTooth(toothNumber);
        setSelectedZone(null);
        setShowAnatomicModal(true);
      } else {
        // Classic view behavior
        if (selectedTooth === toothNumber) {
          setShowToothDetail((prev) => !prev);
        } else {
          setSelectedTooth(toothNumber);
          setSelectedZone(null);
          setShowToothDetail(true);
        }
      }
      setSelectedCondition(null);
      setSeverity(null);
      setNotes("");
    },
    [selectedTooth, isAnatomic],
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

  /** Apply handler for the anatomic modal (receives all data at once) */
  const handleAnatomicApply = React.useCallback(
    (data: {
      tooth_number: number;
      zone: string;
      condition_code: string;
      severity: string | null;
      notes: string | null;
      source: "manual";
    }) => {
      updateCondition(
        {
          patientId,
          data: data as ConditionCreateValues,
        },
        {
          onSuccess: () => {
            // Don't close modal — let the user add more conditions
          },
        },
      );
    },
    [patientId, updateCondition],
  );

  const handleDentitionChange = React.useCallback(
    (type: DentitionType) => {
      if (type === dentitionType) return;
      toggleDentition({
        patientId,
        data: { dentition_type: type },
      });
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
    setShowAnatomicModal(false);
  }, []);

  const handleOpenToothHistory = React.useCallback((toothNumber: number) => {
    setHistoryToothFilter(toothNumber);
    setShowHistory(true);
    setShowToothDetail(false);
    setShowAnatomicModal(false);
  }, []);

  const handleViewModeChange = React.useCallback((mode: ViewMode) => {
    setViewMode(mode);
    // Clear selection when switching views
    setSelectedTooth(null);
    setSelectedZone(null);
    setSelectedCondition(null);
    setShowToothDetail(false);
    setShowAnatomicModal(false);
  }, []);

  const handleAnatomicModalClose = React.useCallback(() => {
    setShowAnatomicModal(false);
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
        viewMode={viewMode}
        onViewModeChange={handleViewModeChange}
        canUseAnatomic={canUseAnatomic}
      />

      {/* ─── Mobile guard for anatomic view ──────────────────────────── */}
      {viewMode === "anatomic" && isMobile && (
        <Card>
          <CardContent className="py-8 text-center">
            <Monitor className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))] mb-3" />
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              El odontograma anatomico requiere una pantalla mas grande.
            </p>
            <button
              type="button"
              onClick={() => setViewMode("classic")}
              className="mt-2 text-sm text-primary-600 hover:underline"
            >
              Cambiar a vista clasica
            </button>
          </CardContent>
        </Card>
      )}

      {/* ─── Main Content ────────────────────────────────────────────── */}
      {!(viewMode === "anatomic" && isMobile) && (
        <div className={cn(
          "flex flex-col gap-4",
          !isAnatomic && "lg:flex-row",
        )}>
          {/* Main view area */}
          {isAnatomic ? (
            /* ── Anatomic Arch View ──────────────────────────────────── */
            <div className="flex-1">
              <React.Suspense fallback={<Skeleton className="h-[420px] w-full rounded-2xl" />}>
                <ToothArchSVG
                  teeth={odontogram?.teeth ?? []}
                  dentitionType={dentitionType}
                  selectedTooth={selectedTooth}
                  onToothClick={handleToothClick}
                  readOnly={!canWrite}
                />
              </React.Suspense>
            </div>
          ) : (
            /* ── Classic Grid View ───────────────────────────────────── */
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
          )}

          {/* Sidebar: Only show in classic view or for history in anatomic */}
          <div className={cn(
            "shrink-0 space-y-4",
            isAnatomic ? "w-full" : "w-full lg:w-80",
          )}>
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

            {/* Classic-only panels */}
            {!isAnatomic && (
              <>
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
              </>
            )}
          </div>
        </div>
      )}

      {/* ─── Anatomic Tooth Detail Modal ─────────────────────────────── */}
      {isAnatomic && showAnatomicModal && selectedTooth && selectedToothData && (
        <React.Suspense fallback={null}>
          <ToothDetailModal
            toothNumber={selectedTooth}
            toothData={selectedToothData}
            conditions={catalog ?? []}
            onApply={handleAnatomicApply}
            onClose={handleAnatomicModalClose}
            onOpenHistory={handleOpenToothHistory}
            isSaving={isUpdating}
            readOnly={!canWrite}
          />
        </React.Suspense>
      )}

      {/* ─── Status Bar ──────────────────────────────────────────────── */}
      <Card>
        <CardContent className="py-2 px-4">
          <div className="flex flex-wrap items-center gap-4 text-xs text-[hsl(var(--muted-foreground))]">
            {/* Anatomic mode: dental health summary */}
            {isAnatomic && odontogram?.teeth && (
              <>
                <span>
                  <span className="font-medium text-green-500">
                    {computeHealthyPercentage(odontogram.teeth)}% sano
                  </span>
                </span>
                <span className="hidden sm:inline">&mdash;</span>
              </>
            )}

            <span>
              <span className={cn(
                "font-medium",
                isAnatomic ? "text-amber-400" : "text-foreground",
              )}>
                {odontogram?.total_conditions ?? 0}
              </span>{" "}
              hallazgo{(odontogram?.total_conditions ?? 0) !== 1 ? "s" : ""}
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
