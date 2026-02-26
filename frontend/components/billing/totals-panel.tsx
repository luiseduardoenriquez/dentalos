"use client";

import * as React from "react";
import { useFormContext, Controller } from "react-hook-form";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { formatCurrency } from "@/lib/utils";

const IVA_RATE = 0.19;

interface TotalsPanelProps {
  applyIva: boolean;
  onApplyIvaChange: (value: boolean) => void;
}

export function TotalsPanel({ applyIva, onApplyIvaChange }: TotalsPanelProps) {
  const { watch } = useFormContext();
  const items = watch("items") || [];

  const subtotal = items.reduce((sum: number, item: Record<string, string>) => {
    const qty = parseInt(item.quantity || "0", 10) || 0;
    const price = parseInt(item.unit_price_display || "0", 10) || 0;
    const disc = parseInt(item.discount_display || "0", 10) || 0;
    return sum + Math.max(0, qty * price * 100 - disc * 100);
  }, 0);

  const ivaAmount = applyIva ? Math.round(subtotal * IVA_RATE) : 0;
  const grandTotal = subtotal + ivaAmount;

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="ml-auto max-w-xs space-y-3">
          {/* Subtotal */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-[hsl(var(--muted-foreground))]">Subtotal</span>
            <span className="tabular-nums font-medium">
              {formatCurrency(subtotal, "COP")}
            </span>
          </div>

          {/* IVA toggle */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Checkbox
                id="apply-iva"
                checked={applyIva}
                onCheckedChange={(checked) => onApplyIvaChange(checked === true)}
              />
              <label
                htmlFor="apply-iva"
                className="text-sm text-[hsl(var(--muted-foreground))] cursor-pointer"
              >
                IVA (19%)
              </label>
            </div>
            <span className="tabular-nums text-sm font-medium">
              {formatCurrency(ivaAmount, "COP")}
            </span>
          </div>

          <Separator />

          {/* Grand total */}
          <div className="flex items-center justify-between">
            <span className="text-base font-semibold text-foreground">Total</span>
            <span className="text-lg font-bold text-foreground tabular-nums">
              {formatCurrency(grandTotal, "COP")}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
