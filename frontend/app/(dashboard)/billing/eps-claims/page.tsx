"use client";

import * as React from "react";
import Link from "next/link";
import { FileText, Plus, Clock } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/pagination";
import { EPSClaimsTable } from "@/components/billing/eps-claims-table";
import { useEPSClaims, useEPSClaimsAging } from "@/lib/hooks/use-eps-claims";
import { formatCurrency } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

// ─── Aging card ───────────────────────────────────────────────────────────────

interface AgingCardProps {
  label: string;
  amount: number;
  colorClass: string;
}

function AgingCard({ label, amount, colorClass }: AgingCardProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-1">
          <Clock className={`h-4 w-4 shrink-0 ${colorClass}`} />
          <p className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
            {label}
          </p>
        </div>
        <p className={`text-lg font-bold tabular-nums ${colorClass}`}>
          {formatCurrency(amount, "COP")}
        </p>
      </CardContent>
    </Card>
  );
}

function AgingSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4 space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-28" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * EPS claims list page — shows paginated claims, status filter, aging summary
 * cards, and a button to create new claims.
 */
export default function EPSClaimsPage() {
  const [page, setPage] = React.useState(1);
  const [status, setStatus] = React.useState<string>("all");

  const { data, isLoading } = useEPSClaims(page, PAGE_SIZE, status);
  const { data: aging, isLoading: agingLoading } = useEPSClaimsAging();

  const claims = data?.items ?? [];
  const total = data?.total ?? 0;

  function handleStatusChange(value: string) {
    setStatus(value);
    setPage(1);
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Reclamaciones EPS
          </h1>
        </div>
        <Button asChild>
          <Link href="/billing/eps-claims/new">
            <Plus className="mr-1.5 h-4 w-4" />
            Nueva reclamación
          </Link>
        </Button>
      </div>

      {/* Aging summary */}
      {agingLoading ? (
        <AgingSkeleton />
      ) : aging ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <AgingCard
            label="0–30 días"
            amount={aging["0_30"]}
            colorClass="text-green-600 dark:text-green-400"
          />
          <AgingCard
            label="31–60 días"
            amount={aging["31_60"]}
            colorClass="text-yellow-600 dark:text-yellow-400"
          />
          <AgingCard
            label="61–90 días"
            amount={aging["61_90"]}
            colorClass="text-orange-600 dark:text-orange-400"
          />
          <AgingCard
            label="+90 días"
            amount={aging["90_plus"]}
            colorClass="text-red-600 dark:text-red-400"
          />
        </div>
      ) : null}

      {/* Status filter */}
      <div className="flex items-end gap-3">
        <div className="space-y-1">
          <label
            htmlFor="eps-status-filter"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Estado
          </label>
          <Select value={status} onValueChange={handleStatusChange}>
            <SelectTrigger id="eps-status-filter" className="w-48">
              <SelectValue placeholder="Todos los estados" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los estados</SelectItem>
              <SelectItem value="draft">Borrador</SelectItem>
              <SelectItem value="submitted">Enviada</SelectItem>
              <SelectItem value="acknowledged">Confirmada</SelectItem>
              <SelectItem value="paid">Pagada</SelectItem>
              <SelectItem value="rejected">Rechazada</SelectItem>
              <SelectItem value="appealed">Apelada</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">
            {total > 0
              ? `${total} reclamación${total !== 1 ? "es" : ""}`
              : "Reclamaciones"}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <EPSClaimsTable claims={claims} isLoading={isLoading} />
        </CardContent>
      </Card>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onChange={setPage}
        />
      )}
    </div>
  );
}
