"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Star, ArrowRight, CheckCircle2 } from "lucide-react";
import { formatCurrency, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface LoyaltyRedemptionDialogProps {
  open: boolean;
  onClose: () => void;
  pointsBalance: number;
  pointsToCurrencyRatio: number;
  patientId: string;
}

interface RedeemPayload {
  patient_id: string;
  points_to_redeem: number;
}

interface RedeemResponse {
  points_redeemed: number;
  discount_cents: number;
  new_balance: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function LoyaltyRedemptionDialog({
  open,
  onClose,
  pointsBalance,
  pointsToCurrencyRatio,
  patientId,
}: LoyaltyRedemptionDialogProps) {
  const queryClient = useQueryClient();
  const [pointsInput, setPointsInput] = React.useState("");
  const [success, setSuccess] = React.useState<RedeemResponse | null>(null);

  const pointsToRedeem = parseInt(pointsInput, 10) || 0;
  const discountCents = Math.floor(
    (pointsToRedeem / pointsToCurrencyRatio) * 100,
  );
  const isValidAmount =
    pointsToRedeem > 0 && pointsToRedeem <= pointsBalance;

  const { mutate: redeem, isPending } = useMutation({
    mutationFn: (payload: RedeemPayload) =>
      apiPost<RedeemResponse>("/loyalty/redeem", payload),
    onSuccess: (data) => {
      setSuccess(data);
      queryClient.invalidateQueries({ queryKey: ["portal-loyalty"] });
      queryClient.invalidateQueries({ queryKey: ["patients", patientId, "loyalty"] });
    },
  });

  function handleConfirm() {
    if (!isValidAmount) return;
    redeem({ patient_id: patientId, points_to_redeem: pointsToRedeem });
  }

  function handleClose() {
    setPointsInput("");
    setSuccess(null);
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Canjear puntos de lealtad</DialogTitle>
          <DialogDescription>
            Convierte tus puntos en descuento para la próxima factura.
          </DialogDescription>
        </DialogHeader>

        {success ? (
          /* ─── Success state ──────────────────────────────────────────── */
          <div className="flex flex-col items-center gap-4 py-4 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-500" />
            <div>
              <p className="text-base font-semibold text-foreground">
                ¡Canje exitoso!
              </p>
              <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                Se aplicaron{" "}
                <span className="font-medium text-foreground">
                  {success.points_redeemed.toLocaleString("es-CO")} puntos
                </span>{" "}
                equivalentes a{" "}
                <span className="font-semibold text-green-600 dark:text-green-400">
                  {formatCurrency(success.discount_cents)} de descuento
                </span>
                .
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                Saldo restante: {success.new_balance.toLocaleString("es-CO")} puntos
              </p>
            </div>
            <Button onClick={handleClose} className="w-full">
              Cerrar
            </Button>
          </div>
        ) : (
          /* ─── Redemption form ─────────────────────────────────────────── */
          <>
            {/* Balance display */}
            <div className="rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 px-4 py-3 flex items-center gap-3">
              <Star className="h-5 w-5 fill-primary-500 text-primary-500 shrink-0" />
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Saldo disponible
                </p>
                <p className="text-2xl font-bold tabular-nums text-primary-700 dark:text-primary-300">
                  {pointsBalance.toLocaleString("es-CO")} pts
                </p>
              </div>
            </div>

            {/* Points input */}
            <div className="space-y-1.5">
              <Label htmlFor="points-redeem">Puntos a canjear</Label>
              <Input
                id="points-redeem"
                type="number"
                min={1}
                max={pointsBalance}
                placeholder="0"
                value={pointsInput}
                onChange={(e) => setPointsInput(e.target.value)}
                autoFocus
              />
              {pointsToRedeem > pointsBalance && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  No puedes canjear más de {pointsBalance.toLocaleString("es-CO")} puntos.
                </p>
              )}
            </div>

            {/* Preview */}
            {pointsToRedeem > 0 && isValidAmount && (
              <div
                className={cn(
                  "flex items-center justify-center gap-3 rounded-lg",
                  "border border-green-200 dark:border-green-800",
                  "bg-green-50 dark:bg-green-900/20 px-4 py-3",
                  "animate-in fade-in-0 duration-200",
                )}
              >
                <span className="text-sm font-medium text-foreground">
                  {pointsToRedeem.toLocaleString("es-CO")} pts
                </span>
                <ArrowRight className="h-4 w-4 text-green-600" />
                <span className="text-base font-bold text-green-700 dark:text-green-300">
                  {formatCurrency(discountCents)} descuento
                </span>
              </div>
            )}

            <p className="text-xs text-[hsl(var(--muted-foreground))] text-center">
              Ratio: {pointsToCurrencyRatio} puntos = $1 COP
            </p>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={isPending}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                onClick={handleConfirm}
                disabled={isPending || !isValidAmount}
              >
                {isPending ? "Canjeando..." : "Confirmar canje"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
