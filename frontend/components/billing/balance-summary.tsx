"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatCurrency, cn } from "@/lib/utils";

interface BalanceSummaryProps {
  subtotal: number; // cents
  tax: number; // cents
  total: number; // cents
  amountPaid: number; // cents
  balance: number; // cents
}

export function BalanceSummary({
  subtotal,
  tax,
  total,
  amountPaid,
  balance,
}: BalanceSummaryProps) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="ml-auto max-w-xs space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[hsl(var(--muted-foreground))]">Subtotal</span>
            <span className="tabular-nums font-medium">
              {formatCurrency(subtotal, "COP")}
            </span>
          </div>
          {tax > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-[hsl(var(--muted-foreground))]">
                IVA (19%)
              </span>
              <span className="tabular-nums font-medium">
                {formatCurrency(tax, "COP")}
              </span>
            </div>
          )}
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-base font-semibold text-foreground">Total</span>
            <span className="text-lg font-bold text-foreground tabular-nums">
              {formatCurrency(total, "COP")}
            </span>
          </div>
          <Separator />
          <div className="flex items-center justify-between text-sm">
            <span className="text-[hsl(var(--muted-foreground))]">Pagado</span>
            <span className="tabular-nums font-medium text-green-600">
              {formatCurrency(amountPaid, "COP")}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-foreground">
              Saldo pendiente
            </span>
            <span
              className={cn(
                "text-base font-bold tabular-nums",
                balance > 0 ? "text-orange-600" : "text-green-600",
              )}
            >
              {formatCurrency(balance, "COP")}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
