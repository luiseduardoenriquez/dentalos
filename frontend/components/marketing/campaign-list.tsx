"use client";

import * as React from "react";
import { RefreshCw, Mail } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import type { EmailCampaign } from "@/app/(dashboard)/marketing/page";

// ─── Status Config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  EmailCampaign["status"],
  { label: string; className: string }
> = {
  draft: {
    label: "Borrador",
    className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  scheduled: {
    label: "Programada",
    className: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  },
  sending: {
    label: "Enviando",
    className: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  },
  sent: {
    label: "Enviada",
    className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  },
  cancelled: {
    label: "Cancelada",
    className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  },
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface CampaignListProps {
  campaigns: EmailCampaign[];
  isLoading: boolean;
  isError?: boolean;
  onSelect: (id: string) => void;
}

// ─── CampaignList ─────────────────────────────────────────────────────────────

export function CampaignList({
  campaigns,
  isLoading,
  isError,
  onSelect,
}: CampaignListProps) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-[hsl(var(--border))]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Enviados</TableHead>
              <TableHead>Abiertos</TableHead>
              <TableHead>Clics</TableHead>
              <TableHead>Creada</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-4 w-48" /></TableCell>
                <TableCell><Skeleton className="h-5 w-20 rounded-full" /></TableCell>
                <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                <TableCell><Skeleton className="h-4 w-20" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center rounded-md border border-[hsl(var(--border))] py-12 gap-2 text-[hsl(var(--muted-foreground))]">
        <RefreshCw className="h-5 w-5" />
        <p className="text-sm">No se pudieron cargar las campañas</p>
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-md border border-[hsl(var(--border))] py-16 gap-3 text-[hsl(var(--muted-foreground))]">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[hsl(var(--muted))]">
          <Mail className="h-7 w-7 opacity-50" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium">Sin campañas</p>
          <p className="text-xs mt-1">
            Crea tu primera campaña de email con el botón "Nueva campaña".
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-[hsl(var(--border))]">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead className="text-right">Enviados</TableHead>
            <TableHead className="text-right">Abiertos</TableHead>
            <TableHead className="text-right">Clics</TableHead>
            <TableHead>Creada</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {campaigns.map((campaign) => {
            const statusCfg = STATUS_CONFIG[campaign.status] ?? {
              label: campaign.status ?? "Desconocido",
              className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
            };
            const totalSent = campaign.total_sent ?? 0;
            const totalOpened = campaign.total_opened ?? 0;
            const totalClicked = campaign.total_clicked ?? 0;
            const openRate =
              totalSent > 0
                ? ((totalOpened / totalSent) * 100).toFixed(1)
                : null;
            const clickRate =
              totalSent > 0
                ? ((totalClicked / totalSent) * 100).toFixed(1)
                : null;

            return (
              <TableRow
                key={campaign.id}
                className="cursor-pointer hover:bg-[hsl(var(--muted))] transition-colors"
                onClick={() => onSelect(campaign.id)}
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && onSelect(campaign.id)}
                role="button"
                aria-label={`Ver campaña ${campaign.name}`}
              >
                {/* Name + subject */}
                <TableCell>
                  <div>
                    <p className="text-sm font-medium">{campaign.name}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] truncate max-w-[240px]">
                      {campaign.subject}
                    </p>
                  </div>
                </TableCell>

                {/* Status badge */}
                <TableCell>
                  <Badge className={cn("text-xs", statusCfg.className)}>
                    {statusCfg.label}
                  </Badge>
                </TableCell>

                {/* Sent count */}
                <TableCell className="text-right tabular-nums text-sm">
                  {totalSent.toLocaleString("es-CO")}
                </TableCell>

                {/* Open rate */}
                <TableCell className="text-right text-sm">
                  {openRate !== null ? (
                    <span>
                      {totalOpened.toLocaleString("es-CO")}{" "}
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        ({openRate}%)
                      </span>
                    </span>
                  ) : (
                    <span className="text-[hsl(var(--muted-foreground))]">—</span>
                  )}
                </TableCell>

                {/* Click rate */}
                <TableCell className="text-right text-sm">
                  {clickRate !== null ? (
                    <span>
                      {totalClicked.toLocaleString("es-CO")}{" "}
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        ({clickRate}%)
                      </span>
                    </span>
                  ) : (
                    <span className="text-[hsl(var(--muted-foreground))]">—</span>
                  )}
                </TableCell>

                {/* Created date */}
                <TableCell className="text-xs text-[hsl(var(--muted-foreground))]">
                  {new Date(campaign.created_at).toLocaleDateString("es-CO", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
