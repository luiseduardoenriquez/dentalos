"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Calendar, Syringe, Clock, Trash2 } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";
import { FaceDiagramSVG } from "@/components/facial-aesthetics/face-diagram-svg";
import { InjectionDetailModal } from "@/components/facial-aesthetics/injection-detail-modal";
import {
  ZONES_BY_ID,
  INJECTION_TYPE_LABELS,
  INJECTION_TYPE_COLORS,
} from "@/lib/facial-aesthetics/zones";
import {
  useFASessions,
  useFASession,
  useCreateFASession,
  useDeleteFASession,
  useAddInjection,
  useUpdateInjection,
  useRemoveInjection,
  useFAHistory,
} from "@/lib/hooks/use-facial-aesthetics";
import type {
  InjectionResponse,
  SessionResponse,
  HistoryEntry,
} from "@/lib/hooks/use-facial-aesthetics";

// ─── Page Component ──────────────────────────────────────────────────────────

export default function FacialAestheticsPage() {
  const params = useParams();
  const patientId = params.id as string;

  // State
  const [selectedSessionId, setSelectedSessionId] = React.useState<string | null>(null);
  const [selectedZone, setSelectedZone] = React.useState<string | null>(null);
  const [modalOpen, setModalOpen] = React.useState(false);
  const [showHistory, setShowHistory] = React.useState(false);

  // Queries
  const { data: sessionsData, isLoading: isLoadingSessions } = useFASessions(patientId);
  const { data: sessionDetail, isLoading: isLoadingDetail } = useFASession(
    patientId,
    selectedSessionId,
  );
  const { data: historyData } = useFAHistory(
    patientId,
    selectedSessionId ?? "",
  );

  // Mutations
  const { mutate: createSession, isPending: isCreating } = useCreateFASession();
  const { mutate: deleteSession } = useDeleteFASession();
  const { mutate: addInjection, isPending: isAddingInjection } = useAddInjection();
  const { mutate: updateInjection, isPending: isUpdatingInjection } = useUpdateInjection();
  const { mutate: removeInjection } = useRemoveInjection();

  // Auto-select first session
  React.useEffect(() => {
    if (sessionsData?.items?.length && !selectedSessionId) {
      setSelectedSessionId(sessionsData.items[0].id);
    }
  }, [sessionsData, selectedSessionId]);

  // Handlers
  const handleCreateSession = () => {
    createSession({
      patientId,
      data: {
        session_date: new Date().toISOString().split("T")[0],
        diagram_type: "face_front",
      },
    });
  };

  const handleDeleteSession = (sessionId: string) => {
    deleteSession({ patientId, sessionId });
    if (selectedSessionId === sessionId) {
      setSelectedSessionId(null);
    }
  };

  const handleZoneClick = (zoneId: string) => {
    setSelectedZone(zoneId);
    setModalOpen(true);
  };

  const existingInjection = React.useMemo(() => {
    if (!selectedZone || !sessionDetail) return null;
    return (
      sessionDetail.injections.find(
        (inj) => inj.zone_id === selectedZone,
      ) ?? null
    );
  }, [selectedZone, sessionDetail]);

  const handleSaveInjection = (data: Record<string, unknown>) => {
    if (!selectedSessionId || !selectedZone) return;

    if (existingInjection) {
      updateInjection({
        patientId,
        sessionId: selectedSessionId,
        injectionId: existingInjection.id,
        data,
      });
    } else {
      addInjection({
        patientId,
        sessionId: selectedSessionId,
        data: { ...data, zone_id: selectedZone },
      });
    }
    setModalOpen(false);
    setSelectedZone(null);
  };

  const handleRemoveInjection = () => {
    if (!selectedSessionId || !existingInjection) return;
    removeInjection({
      patientId,
      sessionId: selectedSessionId,
      injectionId: existingInjection.id,
    });
    setModalOpen(false);
    setSelectedZone(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Estética Facial</h2>
          <p className="text-muted-foreground">
            Registro de puntos de inyección y seguimiento de sesiones
          </p>
        </div>
        <Button onClick={handleCreateSession} disabled={isCreating}>
          <Plus className="mr-2 h-4 w-4" />
          Nueva Sesión
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Sessions List (left column) */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Sesiones</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {isLoadingSessions ? (
                <div className="space-y-2 p-4">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : !sessionsData?.items?.length ? (
                <div className="p-6 text-center text-sm text-muted-foreground">
                  <Syringe className="mx-auto mb-2 h-8 w-8 opacity-40" />
                  No hay sesiones registradas
                </div>
              ) : (
                <div className="divide-y">
                  {sessionsData.items.map((session: SessionResponse) => (
                    <button
                      key={session.id}
                      onClick={() => setSelectedSessionId(session.id)}
                      className={cn(
                        "flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-muted/50",
                        selectedSessionId === session.id && "bg-muted",
                      )}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-sm font-medium">
                            {formatDate(session.session_date)}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {session.injection_count} punto{session.injection_count !== 1 ? "s" : ""}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSession(session.id);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* History panel */}
          {selectedSessionId && (
            <Card className="mt-4">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Historial</CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowHistory(!showHistory)}
                  >
                    <Clock className="mr-1 h-3.5 w-3.5" />
                    {showHistory ? "Ocultar" : "Ver"}
                  </Button>
                </div>
              </CardHeader>
              {showHistory && (
                <CardContent className="max-h-64 overflow-y-auto p-0">
                  {historyData?.items?.length ? (
                    <div className="divide-y">
                      {historyData.items.map((entry: HistoryEntry) => (
                        <div key={entry.id} className="px-4 py-2.5">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={cn(
                                "inline-block h-2 w-2 rounded-full",
                                entry.action === "add" && "bg-green-500",
                                entry.action === "update" && "bg-blue-500",
                                entry.action === "remove" && "bg-red-500",
                              )}
                            />
                            <span className="text-xs font-medium">
                              {entry.action === "add" && "Agregó"}
                              {entry.action === "update" && "Actualizó"}
                              {entry.action === "remove" && "Eliminó"}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {ZONES_BY_ID.get(entry.zone_id)?.label ?? entry.zone_id}
                            </span>
                          </div>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {INJECTION_TYPE_LABELS[entry.injection_type] ?? entry.injection_type}
                            {entry.performed_by_name && ` · ${entry.performed_by_name}`}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="p-4 text-center text-xs text-muted-foreground">
                      Sin historial
                    </p>
                  )}
                </CardContent>
              )}
            </Card>
          )}
        </div>

        {/* Face Diagram (center) */}
        <div className="lg:col-span-5">
          <Card>
            <CardContent className="p-4">
              {isLoadingDetail && selectedSessionId ? (
                <Skeleton className="h-[560px] w-full rounded-lg" />
              ) : selectedSessionId && sessionDetail ? (
                <FaceDiagramSVG
                  injections={sessionDetail.injections}
                  onZoneClick={handleZoneClick}
                  selectedZone={selectedZone}
                />
              ) : (
                <div className="flex h-[400px] items-center justify-center text-sm text-muted-foreground">
                  Selecciona o crea una sesión para comenzar
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Injection Details (right column) */}
        <div className="lg:col-span-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Puntos de Inyección</CardTitle>
            </CardHeader>
            <CardContent>
              {!sessionDetail?.injections?.length ? (
                <p className="text-center text-sm text-muted-foreground">
                  {selectedSessionId
                    ? "Haz clic en el diagrama para agregar puntos"
                    : "Selecciona una sesión"}
                </p>
              ) : (
                <div className="space-y-3">
                  {sessionDetail.injections.map((inj: InjectionResponse) => {
                    const zone = ZONES_BY_ID.get(inj.zone_id);
                    return (
                      <button
                        key={inj.id}
                        onClick={() => handleZoneClick(inj.zone_id)}
                        className="flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50"
                      >
                        <div
                          className="mt-0.5 h-3 w-3 shrink-0 rounded-full"
                          style={{
                            backgroundColor:
                              INJECTION_TYPE_COLORS[inj.injection_type] ?? "#6B7280",
                          }}
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium">
                            {zone?.label ?? inj.zone_id}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {INJECTION_TYPE_LABELS[inj.injection_type] ?? inj.injection_type}
                            {inj.product_name && ` · ${inj.product_name}`}
                          </p>
                          {(inj.dose_units || inj.dose_volume_ml) && (
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              {inj.dose_units != null && `${inj.dose_units}U`}
                              {inj.dose_units != null && inj.dose_volume_ml != null && " / "}
                              {inj.dose_volume_ml != null && `${inj.dose_volume_ml}ml`}
                            </p>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Legend */}
          <Card className="mt-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Leyenda</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(INJECTION_TYPE_LABELS).map(([key, label]) => (
                  <div key={key} className="flex items-center gap-2">
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: INJECTION_TYPE_COLORS[key] }}
                    />
                    <span className="text-xs text-muted-foreground">{label}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Injection Modal */}
      <InjectionDetailModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setSelectedZone(null);
        }}
        zoneId={selectedZone ?? ""}
        zoneName={ZONES_BY_ID.get(selectedZone ?? "")?.label ?? ""}
        existingInjection={existingInjection}
        onSave={handleSaveInjection}
        onRemove={existingInjection ? handleRemoveInjection : undefined}
        isSaving={isAddingInjection || isUpdatingInjection}
      />
    </div>
  );
}
