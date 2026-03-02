"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
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
  ChevronLeft,
  RefreshCw,
  Play,
  Pause,
  Send,
  Mail,
  Calendar,
  ArrowRight,
  Users,
  AlertCircle,
} from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CampaignStep {
  id: string;
  day_offset: number;
  channel: string;
  message_template: string;
  sent_count: number;
  delivered_count: number;
  opened_count: number;
}

interface RecipientRow {
  patient_id: string;
  patient_name: string;
  phone: string | null;
  email: string | null;
  status: string;
  last_updated: string;
  booked: boolean;
}

interface CampaignDetail {
  id: string;
  name: string;
  campaign_type: string;
  status: "draft" | "active" | "paused" | "completed";
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  opened_count: number;
  booked_count: number;
  created_at: string;
  steps: CampaignStep[];
  recipients: RecipientRow[];
}

// ─── Status labels ────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  draft: "Borrador",
  active: "Activa",
  paused: "Pausada",
  completed: "Completada",
};

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "success" | "destructive"> = {
  draft: "secondary",
  active: "success",
  paused: "default",
  completed: "secondary",
};

// ─── Funnel bar ───────────────────────────────────────────────────────────────

function FunnelStep({
  label,
  count,
  total,
  icon: Icon,
  color,
}: {
  label: string;
  count: number;
  total: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0.0";
  return (
    <div className="flex flex-col items-center gap-2 min-w-[100px]">
      <div className={cn("flex h-10 w-10 items-center justify-center rounded-full", color)}>
        <Icon className="h-5 w-5 text-white" />
      </div>
      <div className="text-center">
        <p className="text-lg font-bold tabular-nums">{count.toLocaleString("es-CO")}</p>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
        <p className="text-xs font-medium text-[hsl(var(--muted-foreground))]">{pct}%</p>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RecallCampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const campaignId = params?.id ?? "";
  const queryClient = useQueryClient();

  const { data: campaign, isLoading, isError } = useQuery({
    queryKey: ["recall", "campaigns", campaignId],
    queryFn: () => apiGet<CampaignDetail>(`/recall/campaigns/${campaignId}`),
    staleTime: 30_000,
  });

  const { mutate: toggleStatus, isPending: isToggling } = useMutation({
    mutationFn: (action: "activate" | "pause") =>
      apiPut(`/recall/campaigns/${campaignId}/${action}`, {}),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["recall", "campaigns", campaignId] }),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (isError || !campaign) {
    return (
      <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))] py-10 justify-center">
        <AlertCircle className="h-4 w-4 text-orange-500" />
        No se pudo cargar la campaña.
      </div>
    );
  }

  const canActivate = campaign.status === "draft" || campaign.status === "paused";
  const canPause = campaign.status === "active";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/recall">
              <ChevronLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-foreground">{campaign.name}</h1>
              <Badge
                variant={STATUS_VARIANTS[campaign.status] ?? "secondary"}
                className="text-xs"
              >
                {STATUS_LABELS[campaign.status]}
              </Badge>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
              Creada el {formatDate(campaign.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {canActivate && (
            <Button
              size="sm"
              onClick={() => toggleStatus("activate")}
              disabled={isToggling}
            >
              <Play className="mr-1.5 h-3.5 w-3.5" />
              {isToggling ? "..." : "Activar"}
            </Button>
          )}
          {canPause && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => toggleStatus("pause")}
              disabled={isToggling}
            >
              <Pause className="mr-1.5 h-3.5 w-3.5" />
              {isToggling ? "..." : "Pausar"}
            </Button>
          )}
        </div>
      </div>

      {/* Funnel */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Embudo de conversión</CardTitle>
          <CardDescription>
            Rendimiento de la campaña — de envío a cita agendada.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center gap-4 flex-wrap py-2">
            <FunnelStep
              label="Destinatarios"
              count={campaign.total_recipients}
              total={campaign.total_recipients}
              icon={Users}
              color="bg-slate-500"
            />
            <ArrowRight className="h-5 w-5 text-[hsl(var(--muted-foreground))]" />
            <FunnelStep
              label="Enviados"
              count={campaign.sent_count}
              total={campaign.total_recipients}
              icon={Send}
              color="bg-blue-500"
            />
            <ArrowRight className="h-5 w-5 text-[hsl(var(--muted-foreground))]" />
            <FunnelStep
              label="Entregados"
              count={campaign.delivered_count}
              total={campaign.total_recipients}
              icon={Mail}
              color="bg-primary-500"
            />
            <ArrowRight className="h-5 w-5 text-[hsl(var(--muted-foreground))]" />
            <FunnelStep
              label="Cita agendada"
              count={campaign.booked_count}
              total={campaign.total_recipients}
              icon={Calendar}
              color="bg-green-500"
            />
          </div>
        </CardContent>
      </Card>

      {/* Steps performance */}
      {campaign.steps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Rendimiento por paso</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Día</TableHead>
                  <TableHead>Canal</TableHead>
                  <TableHead className="text-right">Enviados</TableHead>
                  <TableHead className="text-right">Entregados</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {campaign.steps.map((step) => (
                  <TableRow key={step.id}>
                    <TableCell className="text-sm">Día {step.day_offset}</TableCell>
                    <TableCell className="text-sm capitalize">{step.channel}</TableCell>
                    <TableCell className="text-sm text-right tabular-nums">
                      {step.sent_count}
                    </TableCell>
                    <TableCell className="text-sm text-right tabular-nums">
                      {step.delivered_count}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Recipients sample */}
      {campaign.recipients.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Destinatarios</CardTitle>
            <CardDescription>
              Lista de pacientes incluidos en esta campaña.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Paciente</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Cita agendada</TableHead>
                  <TableHead>Actualizado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {campaign.recipients.map((r) => (
                  <TableRow key={r.patient_id}>
                    <TableCell className="text-sm">
                      <Link
                        href={`/patients/${r.patient_id}`}
                        className="text-primary-600 hover:underline"
                      >
                        {r.patient_name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                      {r.status}
                    </TableCell>
                    <TableCell>
                      {r.booked ? (
                        <Badge variant="success" className="text-xs">Sí</Badge>
                      ) : (
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">No</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatDate(r.last_updated)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
