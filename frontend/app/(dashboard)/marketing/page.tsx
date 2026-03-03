"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Plus, RefreshCw } from "lucide-react";
import { apiGet } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { CampaignList } from "@/components/marketing/campaign-list";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface EmailCampaign {
  id: string;
  name: string;
  subject: string;
  status: "draft" | "scheduled" | "sending" | "sent" | "cancelled";
  template_id: string | null;
  total_sent: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  total_unsubscribed: number;
  scheduled_at: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

interface CampaignListResponse {
  items: EmailCampaign[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Query Key ────────────────────────────────────────────────────────────────

export const campaignsQueryKey = (page: number, pageSize: number) =>
  ["email-campaigns", page, pageSize] as const;

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MarketingPage() {
  const router = useRouter();
  const [page, setPage] = React.useState(1);
  const pageSize = 20;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: campaignsQueryKey(page, pageSize),
    queryFn: () =>
      apiGet<CampaignListResponse>(
        `/marketing/campaigns?page=${page}&page_size=${pageSize}`,
      ),
    staleTime: 60_000,
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {data ? (
            <>
              {data.total.toLocaleString("es-CO")}{" "}
              {data.total === 1 ? "campaña" : "campañas"}
            </>
          ) : null}
        </p>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
            className="gap-1.5"
            aria-label="Actualizar lista"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Actualizar</span>
          </Button>

          <Button
            size="sm"
            onClick={() => router.push("/marketing/new")}
            className="gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" />
            Nueva campaña
          </Button>
        </div>
      </div>

      {/* Campaign table */}
      <CampaignList
        campaigns={data?.items ?? []}
        isLoading={isLoading}
        isError={isError}
        onSelect={(id) => router.push(`/marketing/${id}`)}
      />

      {/* Pagination */}
      {!isLoading && !isError && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Anterior
          </Button>
          <span className="text-sm text-[hsl(var(--muted-foreground))]">
            Página {page} de {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  );
}
