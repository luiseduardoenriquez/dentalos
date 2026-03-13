"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
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
import { Pagination } from "@/components/pagination";
import {
  RefreshCw,
  Plus,
  Send,
  CheckCircle2,
  Users,
  Calendar,
  ArrowRight,
} from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RecallCampaign {
  id: string;
  name: string;
  type: string;
  status: "draft" | "active" | "paused" | "completed";
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  booked_count: number;
  created_at: string;
  next_run_at: string | null;
}

interface CampaignList {
  items: RecallCampaign[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status config ────────────────────────────────────────────────────────────

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

const CAMPAIGN_TYPE_LABELS: Record<string, string> = {
  recall: "Recall",
  reactivation: "Pacientes inactivos",
  birthday: "Cumpleaños",
  treatment_followup: "Seguimiento de tratamiento",
};

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
            <Icon className="h-4 w-4 text-primary-600" />
          </div>
          <div>
            <p className="text-2xl font-bold tabular-nums">{value}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Conversion bar ───────────────────────────────────────────────────────────

function ConversionBar({
  sent,
  delivered,
  booked,
}: {
  sent: number;
  delivered: number;
  booked: number;
}) {
  if (sent === 0) return <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>;

  const deliveredPct = ((delivered / sent) * 100).toFixed(0);
  const bookedPct = ((booked / sent) * 100).toFixed(0);

  return (
    <div className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
      <span>{sent}</span>
      <ArrowRight className="h-3 w-3" />
      <span className="text-primary-600">{delivered} ({deliveredPct}%)</span>
      <ArrowRight className="h-3 w-3" />
      <span className="text-green-600">{booked} ({bookedPct}%)</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RecallCampaignsPage() {
  const [page, setPage] = React.useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["recall", "campaigns", page],
    queryFn: () =>
      apiGet<CampaignList>("/recall/campaigns", { page, page_size: 20 }),
    staleTime: 30_000,
  });

  // Aggregate stats
  const stats = React.useMemo(() => {
    if (!data) return null;
    return {
      total: data.total,
      active: data.items.filter((c) => c.status === "active").length,
      totalSent: data.items.reduce((sum, c) => sum + c.sent_count, 0),
      totalBooked: data.items.reduce((sum, c) => sum + c.booked_count, 0),
    };
  }, [data]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-9 w-40" />
        </div>
        <div className="grid gap-4 sm:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Campañas de recall
          </h1>
        </div>
        <Button asChild>
          <Link href="/recall/new">
            <Plus className="mr-2 h-4 w-4" />
            Nueva campaña
          </Link>
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Campañas totales" value={stats.total} icon={RefreshCw} />
          <StatCard label="Activas" value={stats.active} icon={CheckCircle2} />
          <StatCard label="Mensajes enviados" value={stats.totalSent} icon={Send} />
          <StatCard label="Citas generadas" value={stats.totalBooked} icon={Calendar} />
        </div>
      )}

      {/* Campaign list */}
      <Card>
        <CardHeader>
          <CardTitle>Mis campañas</CardTitle>
          <CardDescription>
            Historial de campañas de recall y sus resultados.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!data || data.items.length === 0 ? (
            <div className="text-center py-10">
              <RefreshCw className="h-10 w-10 mx-auto text-[hsl(var(--muted-foreground))] opacity-40 mb-3" />
              <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
                No hay campañas creadas aún.
              </p>
              <Button asChild>
                <Link href="/recall/new">
                  <Plus className="mr-2 h-4 w-4" />
                  Crear primera campaña
                </Link>
              </Button>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Destinatarios</TableHead>
                    <TableHead>Enviado → Entregado → Cita</TableHead>
                    <TableHead>Próxima ejecución</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((campaign) => (
                    <TableRow key={campaign.id}>
                      <TableCell className="text-sm font-medium">
                        {campaign.name}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {CAMPAIGN_TYPE_LABELS[campaign.type] ?? campaign.type}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={STATUS_VARIANTS[campaign.status] ?? "secondary"}
                          className="text-xs"
                        >
                          {STATUS_LABELS[campaign.status] ?? campaign.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm tabular-nums">
                        <div className="flex items-center gap-1">
                          <Users className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                          {campaign.total_recipients}
                        </div>
                      </TableCell>
                      <TableCell>
                        <ConversionBar
                          sent={campaign.sent_count}
                          delivered={campaign.delivered_count}
                          booked={campaign.booked_count}
                        />
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {campaign.next_run_at ? formatDate(campaign.next_run_at) : "—"}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/recall/${campaign.id}`}>Ver</Link>
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
    </div>
  );
}
