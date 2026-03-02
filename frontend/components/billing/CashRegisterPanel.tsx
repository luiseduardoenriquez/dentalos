"use client";

import * as React from "react";
import Link from "next/link";
import { Landmark, TrendingUp, TrendingDown, Lock, Unlock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { formatCurrency, formatDateTime, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CashRegisterStatus {
  id: string;
  name: string;
  status: "open" | "closed";
  opened_at: string | null;
  opening_balance_cents: number;
  net_balance_cents: number;
  total_income_cents: number;
  total_expense_cents: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CashRegisterPanel() {
  const { data: register, isLoading } = useQuery({
    queryKey: ["cash-register", "current"],
    queryFn: () => apiGet<CashRegisterStatus>("/cash-registers/current"),
    staleTime: 30_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-28" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-9 w-full" />
        </CardContent>
      </Card>
    );
  }

  const isOpen = register?.status === "open";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Landmark className="h-4 w-4 text-primary-600" />
          Caja Registradora
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex h-2 w-2 rounded-full",
              isOpen ? "bg-green-500" : "bg-slate-400",
            )}
          />
          <span
            className={cn(
              "text-sm font-medium",
              isOpen
                ? "text-green-700 dark:text-green-400"
                : "text-[hsl(var(--muted-foreground))]",
            )}
          >
            {isOpen ? "Abierta" : "Cerrada"}
          </span>
          {register && (
            <span className="ml-auto text-xs text-[hsl(var(--muted-foreground))] truncate max-w-[100px]">
              {register.name}
            </span>
          )}
        </div>

        {/* Balance when open */}
        {isOpen && register && (
          <>
            <div className="rounded-lg bg-[hsl(var(--muted)/0.5)] p-3 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1 text-[hsl(var(--muted-foreground))]">
                  <TrendingDown className="h-3 w-3 text-green-500" />
                  Ingresos
                </span>
                <span className="font-semibold tabular-nums text-green-600">
                  {formatCurrency(register.total_income_cents, "COP")}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1 text-[hsl(var(--muted-foreground))]">
                  <TrendingUp className="h-3 w-3 text-red-500" />
                  Egresos
                </span>
                <span className="font-semibold tabular-nums text-red-600">
                  {formatCurrency(register.total_expense_cents, "COP")}
                </span>
              </div>
              <div className="border-t border-[hsl(var(--border))] pt-1.5 flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">Neto</span>
                <span
                  className={cn(
                    "text-sm font-bold tabular-nums",
                    register.net_balance_cents >= 0
                      ? "text-foreground"
                      : "text-red-600",
                  )}
                >
                  {formatCurrency(register.net_balance_cents, "COP")}
                </span>
              </div>
            </div>

            {register.opened_at && (
              <p className="text-[11px] text-[hsl(var(--muted-foreground))]">
                Abierta desde {formatDateTime(register.opened_at)}
              </p>
            )}
          </>
        )}

        {/* Action button */}
        <Button asChild variant={isOpen ? "outline" : "default"} size="sm" className="w-full">
          <Link href="/billing/cash-register">
            {isOpen ? (
              <>
                <Lock className="mr-1.5 h-3.5 w-3.5" />
                Ver / Cerrar caja
              </>
            ) : (
              <>
                <Unlock className="mr-1.5 h-3.5 w-3.5" />
                Abrir caja
              </>
            )}
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
