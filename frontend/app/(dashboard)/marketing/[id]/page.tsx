"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  RefreshCw,
  Send,
  Trash2,
  XCircle,
} from "lucide-react";
import { apiGet, apiPost, apiDelete } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CampaignStats } from "@/components/marketing/campaign-stats";
import type { EmailCampaign } from "@/app/(dashboard)/marketing/page";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CampaignRecipient {
  id: string;
  patient_id: string;
  patient_name: string;
  email: string;
  status: "pending" | "sent" | "opened" | "clicked" | "bounced" | "unsubscribed";
  sent_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
}

interface RecipientListResponse {
  items: CampaignRecipient[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status Config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  EmailCampaign["status"],
  { label: string; className: string }
> = {
  draft: { label: "Borrador", className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300" },
  scheduled: { label: "Programada", className: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
  sending: { label: "Enviando", className: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300" },
  sent: { label: "Enviada", className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300" },
  cancelled: { label: "Cancelada", className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" },
};

const RECIPIENT_STATUS_CONFIG: Record<
  CampaignRecipient["status"],
  { label: string; className: string }
> = {
  pending: { label: "Pendiente", className: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" },
  sent: { label: "Enviado", className: "bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-300" },
  opened: { label: "Abierto", className: "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300" },
  clicked: { label: "Clic", className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300" },
  bounced: { label: "Rebotado", className: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300" },
  unsubscribed: { label: "Desuscrito", className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" },
};

// ─── Query Keys ───────────────────────────────────────────────────────────────

const campaignDetailKey = (id: string) => ["email-campaign", id] as const;
const campaignRecipientsKey = (id: string, page: number) =>
  ["email-campaign-recipients", id, page] as const;

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { success, error } = useToast();
  const campaignId = params.id;
  const [recipientsPage, setRecipientsPage] = React.useState(1);
  const recipientsPageSize = 20;

  // Fetch campaign detail
  const {
    data: campaign,
    isLoading,
    isError,
  } = useQuery({
    queryKey: campaignDetailKey(campaignId),
    queryFn: () => apiGet<EmailCampaign>(`/marketing/campaigns/${campaignId}`),
    staleTime: 30_000,
  });

  // Fetch recipients
  const { data: recipientsData, isLoading: isLoadingRecipients } = useQuery({
    queryKey: campaignRecipientsKey(campaignId, recipientsPage),
    queryFn: () =>
      apiGet<RecipientListResponse>(
        `/marketing/campaigns/${campaignId}/recipients?page=${recipientsPage}&page_size=${recipientsPageSize}`,
      ),
    enabled: Boolean(campaign),
    staleTime: 60_000,
  });

  // Send campaign
  const { mutate: sendCampaign, isPending: isSending } = useMutation({
    mutationFn: () =>
      apiPost<EmailCampaign>(`/marketing/campaigns/${campaignId}/send`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: campaignDetailKey(campaignId) });
      queryClient.invalidateQueries({ queryKey: ["email-campaigns"] });
      success("Campaña enviada", "El envío masivo fue iniciado.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo iniciar el envío.";
      error("Error al enviar", message);
    },
  });

  // Cancel campaign
  const { mutate: cancelCampaign, isPending: isCancelling } = useMutation({
    mutationFn: () =>
      apiPost<EmailCampaign>(`/marketing/campaigns/${campaignId}/cancel`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: campaignDetailKey(campaignId) });
      queryClient.invalidateQueries({ queryKey: ["email-campaigns"] });
      success("Campaña cancelada");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo cancelar la campaña.";
      error("Error al cancelar", message);
    },
  });

  // Delete campaign
  const { mutate: deleteCampaign, isPending: isDeleting } = useMutation({
    mutationFn: () => apiDelete<void>(`/marketing/campaigns/${campaignId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-campaigns"] });
      success("Campaña eliminada");
      router.push("/marketing");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo eliminar la campaña.";
      error("Error al eliminar", message);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
      </div>
    );
  }

  if (isError || !campaign) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-[hsl(var(--muted-foreground))]">
        <p className="text-base">No se pudo cargar la campaña.</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push("/marketing")}
        >
          Volver a campañas
        </Button>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[campaign.status];
  const totalRecipientsPages = recipientsData
    ? Math.ceil(recipientsData.total / recipientsPageSize)
    : 1;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/marketing")}
            className="gap-1.5 mt-0.5 -ml-2 shrink-0"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold">{campaign.name}</h2>
              <Badge className={cn("text-xs", statusConfig.className)}>
                {statusConfig.label}
              </Badge>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
              Asunto: {campaign.subject}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Send (only if draft) */}
          {campaign.status === "draft" && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" className="gap-1.5" disabled={isSending}>
                  <Send className="h-3.5 w-3.5" />
                  Enviar ahora
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Enviar campaña?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Se enviará el email a todos los destinatarios del segmento.
                    Esta acción no se puede deshacer.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction onClick={() => sendCampaign()}>
                    Sí, enviar
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}

          {/* Cancel (if scheduled or sending) */}
          {(campaign.status === "scheduled" || campaign.status === "sending") && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-orange-600 border-orange-300 hover:bg-orange-50"
              onClick={() => cancelCampaign()}
              disabled={isCancelling}
            >
              <XCircle className="h-3.5 w-3.5" />
              Cancelar envío
            </Button>
          )}

          {/* Delete (if draft or cancelled) */}
          {(campaign.status === "draft" || campaign.status === "cancelled") && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-red-600 border-red-300 hover:bg-red-50"
                  disabled={isDeleting}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Eliminar
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Eliminar campaña?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Esta acción es irreversible. La campaña y todos sus datos
                    serán eliminados permanentemente.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => deleteCampaign()}
                    className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                  >
                    Sí, eliminar
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      {/* Stats */}
      <CampaignStats
        stats={{
          total_sent: campaign.total_sent,
          total_opened: campaign.total_opened,
          total_clicked: campaign.total_clicked,
          total_bounced: campaign.total_bounced,
          total_unsubscribed: campaign.total_unsubscribed,
        }}
      />

      {/* Recipients table */}
      <div className="flex flex-col gap-3">
        <h3 className="text-base font-semibold">
          Destinatarios
          {recipientsData && (
            <span className="ml-2 text-sm font-normal text-[hsl(var(--muted-foreground))]">
              ({recipientsData.total.toLocaleString("es-CO")})
            </span>
          )}
        </h3>

        {isLoadingRecipients ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-4 w-4 animate-spin text-[hsl(var(--muted-foreground))]" />
          </div>
        ) : (
          <>
            <div className="rounded-md border border-[hsl(var(--border))]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Paciente</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Enviado</TableHead>
                    <TableHead>Abierto</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recipientsData?.items.length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className="py-8 text-center text-[hsl(var(--muted-foreground))]"
                      >
                        Sin destinatarios
                      </TableCell>
                    </TableRow>
                  )}
                  {recipientsData?.items.map((recipient) => {
                    const rStatus = RECIPIENT_STATUS_CONFIG[recipient.status];
                    return (
                      <TableRow key={recipient.id}>
                        <TableCell className="font-medium">
                          {recipient.patient_name}
                        </TableCell>
                        <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                          {recipient.email}
                        </TableCell>
                        <TableCell>
                          <Badge className={cn("text-xs", rStatus.className)}>
                            {rStatus.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-[hsl(var(--muted-foreground))]">
                          {recipient.sent_at
                            ? new Date(recipient.sent_at).toLocaleString("es-CO", {
                                dateStyle: "short",
                                timeStyle: "short",
                              })
                            : "—"}
                        </TableCell>
                        <TableCell className="text-xs text-[hsl(var(--muted-foreground))]">
                          {recipient.opened_at
                            ? new Date(recipient.opened_at).toLocaleString("es-CO", {
                                dateStyle: "short",
                                timeStyle: "short",
                              })
                            : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {totalRecipientsPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={recipientsPage === 1}
                  onClick={() => setRecipientsPage((p) => p - 1)}
                >
                  Anterior
                </Button>
                <span className="text-sm text-[hsl(var(--muted-foreground))]">
                  Página {recipientsPage} de {totalRecipientsPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={recipientsPage >= totalRecipientsPages}
                  onClick={() => setRecipientsPage((p) => p + 1)}
                >
                  Siguiente
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
