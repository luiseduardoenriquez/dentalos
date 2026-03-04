"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Pagination } from "@/components/pagination";
import {
  ClipboardList,
  CheckCircle2,
  XCircle,
  Eye,
  AlertCircle,
} from "lucide-react";
import { formatDate } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface IntakeSubmission {
  id: string;
  template_name: string;
  patient_name: string;
  patient_email: string | null;
  patient_phone: string;
  submitted_at: string;
  status: "pending" | "approved" | "rejected";
  responses: Array<{ label: string; value: string }> | null;
  matched_patient_id: string | null;
}

interface SubmissionList {
  items: IntakeSubmission[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobado",
  rejected: "Rechazado",
};

const STATUS_VARIANTS: Record<string, "default" | "success" | "destructive"> = {
  pending: "default",
  approved: "success",
  rejected: "destructive",
};

// ─── Detail dialog ────────────────────────────────────────────────────────────

function SubmissionDetailDialog({
  submission,
  onClose,
  onApprove,
  onReject,
  isProcessing,
}: {
  submission: IntakeSubmission;
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  isProcessing: boolean;
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Solicitud de {submission.patient_name}</DialogTitle>
          <DialogDescription>
            {submission.template_name} · {formatDate(submission.submitted_at)}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Contact info */}
          <div className="rounded-lg border p-3 space-y-2 text-sm">
            <p>
              <span className="text-[hsl(var(--muted-foreground))]">Teléfono: </span>
              {submission.patient_phone}
            </p>
            {submission.patient_email && (
              <p>
                <span className="text-[hsl(var(--muted-foreground))]">Correo: </span>
                {submission.patient_email}
              </p>
            )}
            {submission.matched_patient_id && (
              <p>
                <span className="text-[hsl(var(--muted-foreground))]">Paciente vinculado: </span>
                <Link
                  href={`/patients/${submission.matched_patient_id}`}
                  className="text-primary-600 hover:underline"
                  onClick={onClose}
                >
                  Ver paciente
                </Link>
              </p>
            )}
          </div>

          {/* Responses */}
          {(submission.responses ?? []).length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                Respuestas
              </p>
              {(submission.responses ?? []).map((r, idx) => (
                <div key={idx} className="text-sm">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{r.label}</p>
                  <p className="font-medium">{r.value || "—"}</p>
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          {submission.status === "pending" && (
            <div className="flex gap-2 pt-2 border-t border-[hsl(var(--border))]">
              <Button
                className="flex-1"
                onClick={() => onApprove(submission.id)}
                disabled={isProcessing}
              >
                <CheckCircle2 className="mr-2 h-4 w-4" />
                {isProcessing ? "Procesando..." : "Aprobar"}
              </Button>
              <Button
                variant="outline"
                className="flex-1 border-destructive/30 text-destructive hover:bg-destructive/10"
                onClick={() => onReject(submission.id)}
                disabled={isProcessing}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Rechazar
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function IntakeSubmissionsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = React.useState(1);
  const [statusFilter, setStatusFilter] = React.useState<"" | "pending" | "approved" | "rejected">("pending");
  const [viewSubmission, setViewSubmission] = React.useState<IntakeSubmission | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["intake", "submissions", page, statusFilter],
    queryFn: () =>
      apiGet<SubmissionList>("/intake/submissions", {
        page,
        page_size: 20,
        status: statusFilter || undefined,
      }),
    staleTime: 30_000,
  });

  const { mutate: processSubmission, isPending: isProcessing } = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      apiPut(`/intake/submissions/${id}/${action}`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intake", "submissions"] });
      setViewSubmission(null);
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))] py-10 justify-center">
        <AlertCircle className="h-4 w-4 text-orange-500" />
        No se pudieron cargar las solicitudes.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Solicitudes de ingreso
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {(["", "pending", "approved", "rejected"] as const).map((s) => (
            <Button
              key={s}
              variant={statusFilter === s ? "default" : "outline"}
              size="sm"
              onClick={() => { setStatusFilter(s); setPage(1); }}
            >
              {s === "" ? "Todas" : STATUS_LABELS[s]}
            </Button>
          ))}
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Formularios recibidos</CardTitle>
          <CardDescription>
            Revisa, aprueba o rechaza los formularios enviados por pacientes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!data || data.items.length === 0 ? (
            <div className="text-center py-10">
              <ClipboardList className="h-10 w-10 mx-auto text-[hsl(var(--muted-foreground))] opacity-40 mb-3" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No hay solicitudes{statusFilter ? ` con estado "${STATUS_LABELS[statusFilter]}"` : ""}.
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Paciente</TableHead>
                    <TableHead>Formulario</TableHead>
                    <TableHead>Teléfono</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((sub) => (
                    <TableRow key={sub.id}>
                      <TableCell className="text-sm font-medium">
                        {sub.patient_name || <span className="text-[hsl(var(--muted-foreground))] italic">Sin nombre</span>}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {sub.template_name || "—"}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {sub.patient_phone || "—"}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {formatDate(sub.submitted_at)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={STATUS_VARIANTS[sub.status]}
                          className="text-xs"
                        >
                          {STATUS_LABELS[sub.status]}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setViewSubmission(sub)}
                          title="Ver detalle"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {data.total > 20 && (
                <div className="mt-4">
                  <Pagination
                    page={page}
                    pageSize={20}
                    total={data.total}
                    onChange={setPage}
                  />
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Detail dialog */}
      {viewSubmission && (
        <SubmissionDetailDialog
          submission={viewSubmission}
          onClose={() => setViewSubmission(null)}
          onApprove={(id) => processSubmission({ id, action: "approve" })}
          onReject={(id) => processSubmission({ id, action: "reject" })}
          isProcessing={isProcessing}
        />
      )}
    </div>
  );
}
