"use client";

import * as React from "react";
import {
  Landmark,
  TrendingUp,
  TrendingDown,
  Minus,
  Unlock,
  Lock,
  FileText,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { CashMovementList, type CashMovement } from "@/components/billing/CashMovementList";
import { DailyReport } from "@/components/billing/DailyReport";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { formatCurrency, formatDateTime, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CashRegisterDetail {
  id: string;
  name: string;
  location: string | null;
  status: "open" | "closed";
  opened_at: string | null;
  closed_at: string | null;
  opening_balance_cents: number;
  closing_balance_cents: number | null;
  total_income_cents: number;
  total_expense_cents: number;
  net_balance_cents: number;
  movements: CashMovement[];
}

interface OpenRegisterPayload {
  name: string;
  location: string;
  opening_balance_cents: number;
}

interface CloseRegisterPayload {
  closing_balance_cents: number;
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function CashRegisterSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-7 w-48" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  title,
  value,
  icon: Icon,
  iconClass = "text-primary-600",
  iconBgClass = "bg-primary-100 dark:bg-primary-900/20",
  valueClass = "text-foreground",
}: {
  title: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  iconClass?: string;
  iconBgClass?: string;
  valueClass?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg shrink-0",
              iconBgClass,
            )}
          >
            <Icon className={cn("h-5 w-5", iconClass)} />
          </div>
          <div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">{title}</p>
            <p className={cn("text-xl font-bold tabular-nums", valueClass)}>{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Open Form ─────────────────────────────────────────────────────────────────

function OpenRegisterForm({ onOpen }: { onOpen: (payload: OpenRegisterPayload) => void }) {
  const [name, setName] = React.useState("Caja Principal");
  const [location, setLocation] = React.useState("");
  const [openingBalance, setOpeningBalance] = React.useState("");
  const [isPending, setIsPending] = React.useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsPending(true);
    try {
      onOpen({
        name: name.trim(),
        location: location.trim(),
        opening_balance_cents: Math.round(parseFloat(openingBalance || "0") * 100),
      });
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Unlock className="h-4 w-4 text-primary-600" />
          Abrir caja
        </CardTitle>
        <CardDescription>
          Ingresa el saldo inicial del efectivo disponible al abrir.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="register-name">Nombre de la caja</Label>
            <Input
              id="register-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={isPending}
              placeholder="Caja Principal"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="register-location">
              Ubicación{" "}
              <span className="text-[hsl(var(--muted-foreground))] font-normal text-xs">
                (opcional)
              </span>
            </Label>
            <Input
              id="register-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Ej. Consultorio 1"
              disabled={isPending}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="register-opening-balance">Saldo inicial (COP)</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[hsl(var(--muted-foreground))] pointer-events-none">
                $
              </span>
              <Input
                id="register-opening-balance"
                type="text"
                inputMode="decimal"
                placeholder="0"
                className="pl-7 tabular-nums"
                value={openingBalance}
                onChange={(e) => setOpeningBalance(e.target.value)}
                disabled={isPending}
              />
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={isPending}>
            <Unlock className="mr-2 h-4 w-4" />
            {isPending ? "Abriendo..." : "Abrir caja"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ─── Close Form ────────────────────────────────────────────────────────────────

function CloseRegisterForm({
  expectedCents,
  onClose,
}: {
  expectedCents: number;
  onClose: (payload: CloseRegisterPayload) => void;
}) {
  const [closingBalance, setClosingBalance] = React.useState(
    String(Math.round(expectedCents / 100)),
  );
  const [isPending, setIsPending] = React.useState(false);

  const closingCents = Math.round(parseFloat(closingBalance || "0") * 100);
  const difference = closingCents - expectedCents;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsPending(true);
    try {
      onClose({ closing_balance_cents: closingCents });
    } finally {
      setIsPending(false);
    }
  }

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base text-red-700 dark:text-red-400">
          <Lock className="h-4 w-4" />
          Cerrar caja
        </CardTitle>
        <CardDescription>
          Cuenta el efectivo disponible y confirma el saldo de cierre.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-lg bg-[hsl(var(--muted)/0.5)] px-4 py-3 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-[hsl(var(--muted-foreground))]">Saldo esperado</span>
              <span className="font-semibold tabular-nums">
                {formatCurrency(expectedCents, "COP")}
              </span>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="closing-balance">Saldo de cierre real (COP)</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[hsl(var(--muted-foreground))] pointer-events-none">
                $
              </span>
              <Input
                id="closing-balance"
                type="text"
                inputMode="decimal"
                className="pl-7 tabular-nums"
                value={closingBalance}
                onChange={(e) => setClosingBalance(e.target.value)}
                disabled={isPending}
              />
            </div>
            {/* Difference preview */}
            {closingBalance && !isNaN(closingCents) && (
              <p
                className={cn(
                  "text-xs tabular-nums",
                  difference === 0
                    ? "text-green-600"
                    : difference > 0
                    ? "text-blue-600"
                    : "text-red-600 font-medium",
                )}
              >
                Diferencia:{" "}
                {(difference >= 0 ? "+" : "") + formatCurrency(difference, "COP")}
                {difference < 0 && " — revisar antes de cerrar"}
              </p>
            )}
          </div>
          <Button
            type="submit"
            variant="destructive"
            className="w-full"
            disabled={isPending}
          >
            <Lock className="mr-2 h-4 w-4" />
            {isPending ? "Cerrando..." : "Confirmar cierre"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CashRegisterPage() {
  const queryClient = useQueryClient();
  const [showReport, setShowReport] = React.useState(false);

  const {
    data: register,
    isLoading,
    isError,
  } = useQuery<CashRegisterDetail | null>({
    queryKey: ["cash-register", "current"],
    queryFn: async () => {
      try {
        return await apiGet<CashRegisterDetail>("/cash-registers/current");
      } catch {
        return null;
      }
    },
    staleTime: 15_000,
    retry: false,
  });

  const { mutate: openRegister } = useMutation({
    mutationFn: (payload: OpenRegisterPayload) =>
      apiPost("/cash-registers/open", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-register"] });
    },
  });

  const { mutate: closeRegister } = useMutation({
    mutationFn: (payload: CloseRegisterPayload) =>
      apiPost("/cash-registers/close", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-register"] });
    },
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <CashRegisterSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
            No se pudo cargar la caja. Intenta de nuevo.
          </CardContent>
        </Card>
      </div>
    );
  }

  const isOpen = register?.status === "open";
  const expectedClosingCents =
    register
      ? register.opening_balance_cents +
        register.total_income_cents -
        register.total_expense_cents
      : 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Landmark className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Caja Registradora
          </h1>
        </div>
        {isOpen && register && (
          <div className="flex items-center gap-3">
            <Badge
              variant="success"
              className="flex items-center gap-1.5"
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
              Abierta
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowReport((v) => !v)}
            >
              <FileText className="mr-1.5 h-4 w-4" />
              {showReport ? "Ocultar reporte" : "Ver reporte"}
            </Button>
          </div>
        )}
      </div>

      {/* Closed state — open form */}
      {!isOpen && (
        <OpenRegisterForm onOpen={(payload) => openRegister(payload)} />
      )}

      {/* Open state */}
      {isOpen && register && (
        <>
          {/* Summary info */}
          <div className="text-sm text-[hsl(var(--muted-foreground))]">
            <strong className="text-foreground">{register.name}</strong>
            {register.location && (
              <span> &middot; {register.location}</span>
            )}
            {register.opened_at && (
              <span> &middot; Abierta: {formatDateTime(register.opened_at)}</span>
            )}
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard
              title="Total ingresos"
              value={formatCurrency(register.total_income_cents, "COP")}
              icon={TrendingDown}
              iconClass="text-green-600"
              iconBgClass="bg-green-50 dark:bg-green-900/20"
              valueClass="text-green-600"
            />
            <KpiCard
              title="Total egresos"
              value={formatCurrency(register.total_expense_cents, "COP")}
              icon={TrendingUp}
              iconClass="text-red-600"
              iconBgClass="bg-red-50 dark:bg-red-900/20"
              valueClass="text-red-600"
            />
            <KpiCard
              title="Saldo neto"
              value={formatCurrency(register.net_balance_cents, "COP")}
              icon={Minus}
              iconClass={register.net_balance_cents >= 0 ? "text-primary-600" : "text-red-600"}
              valueClass={register.net_balance_cents >= 0 ? "text-foreground" : "text-red-600"}
            />
          </div>

          <Separator />

          {/* Movements */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">
                Movimientos de la sesión
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <CashMovementList
                movements={register.movements ?? []}
                emptyMessage="No hay movimientos aún en esta sesión."
              />
            </CardContent>
          </Card>

          {/* Report */}
          {showReport && (
            <>
              <Separator />
              <DailyReport
                registerName={register.name}
                openedAt={register.opened_at!}
                closedAt={register.closed_at}
                openingBalanceCents={register.opening_balance_cents}
                closingBalanceCents={register.closing_balance_cents}
                totalIncomeCents={register.total_income_cents}
                totalExpenseCents={register.total_expense_cents}
                netBalanceCents={register.net_balance_cents}
                movements={register.movements ?? []}
              />
            </>
          )}

          <Separator />

          {/* Close form */}
          <CloseRegisterForm
            expectedCents={expectedClosingCents}
            onClose={(payload) => closeRegister(payload)}
          />
        </>
      )}
    </div>
  );
}
