"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
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
import { Star, AlertCircle } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type TransactionType = "earned" | "redeemed" | "expired";

interface LoyaltyTransaction {
  id: string;
  created_at: string;
  type: TransactionType;
  points: number;
  reason: string;
}

interface LoyaltyData {
  points_balance: number;
  lifetime_points_earned: number;
  lifetime_points_redeemed: number;
  transactions: LoyaltyTransaction[];
}

// ─── Transaction type config ──────────────────────────────────────────────────

const TRANSACTION_CONFIG: Record<
  TransactionType,
  { label: string; variant: "success" | "secondary" | "destructive"; sign: "+" | "-" }
> = {
  earned: { label: "Ganado", variant: "success", sign: "+" },
  redeemed: { label: "Canjeado", variant: "secondary", sign: "-" },
  expired: { label: "Expirado", variant: "destructive", sign: "-" },
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalLoyaltyPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["portal-loyalty"],
    queryFn: () => apiGet<LoyaltyData>("/portal/loyalty"),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="mx-auto h-40 w-40 rounded-full bg-slate-100 dark:bg-zinc-800" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm text-red-600 dark:text-red-400">
          No se pudo cargar tu programa de puntos.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-lg mx-auto">
      {/* ─── Points Circle ───────────────────────────────────────────────── */}
      <div className="flex flex-col items-center gap-2 pt-4">
        <div
          className={cn(
            "flex h-40 w-40 flex-col items-center justify-center rounded-full",
            "border-4 border-primary-500 dark:border-primary-400",
            "bg-primary-50 dark:bg-primary-900/20 shadow-lg",
          )}
        >
          <Star className="mb-1 h-6 w-6 fill-primary-500 text-primary-500" />
          <p className="text-4xl font-bold tabular-nums text-primary-700 dark:text-primary-300">
            {data.points_balance.toLocaleString("es-CO")}
          </p>
        </div>
        <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
          Puntos acumulados
        </p>
      </div>

      {/* ─── Summary Stats ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-2xl font-bold tabular-nums text-foreground">
              {data.lifetime_points_earned.toLocaleString("es-CO")}
            </p>
            <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
              Puntos ganados totales
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4 text-center">
            <p className="text-2xl font-bold tabular-nums text-foreground">
              {data.lifetime_points_redeemed.toLocaleString("es-CO")}
            </p>
            <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
              Puntos canjeados
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ─── Transaction History ─────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Historial de puntos</CardTitle>
          <CardDescription>
            Movimientos de tu programa de fidelización.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.transactions.length === 0 ? (
            <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No tienes movimientos de puntos aún.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Razón</TableHead>
                  <TableHead className="text-right">Puntos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.transactions.map((tx) => {
                  const config = TRANSACTION_CONFIG[tx.type];
                  return (
                    <TableRow key={tx.id}>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                        {formatDate(tx.created_at)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={config.variant}>{config.label}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-foreground max-w-[160px] truncate">
                        {tx.reason}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right tabular-nums font-semibold",
                          tx.type === "earned"
                            ? "text-green-600 dark:text-green-400"
                            : "text-red-600 dark:text-red-400",
                        )}
                      >
                        {config.sign}
                        {tx.points.toLocaleString("es-CO")}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
