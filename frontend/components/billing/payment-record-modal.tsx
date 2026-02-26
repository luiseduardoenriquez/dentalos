"use client";

import * as React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { DollarSign } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRecordPayment } from "@/lib/hooks/use-payments";
import type { InvoiceResponse } from "@/lib/hooks/use-invoices";
import {
  paymentRecordSchema,
  PAYMENT_METHODS,
  PAYMENT_METHOD_LABELS,
} from "@/lib/validations/payment";
import { formatCurrency } from "@/lib/utils";

interface PaymentRecordModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  patientId: string;
  invoice: InvoiceResponse;
  /** Pre-fill amount in cents (e.g. for installment payments) */
  prefillAmount?: number;
}

export function PaymentRecordModal({
  open,
  onOpenChange,
  patientId,
  invoice,
  prefillAmount,
}: PaymentRecordModalProps) {
  const { mutate: recordPayment, isPending } = useRecordPayment(
    patientId,
    invoice.id,
  );

  const defaultAmount = prefillAmount ?? invoice.balance;

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(paymentRecordSchema),
    defaultValues: {
      amount_display: String(Math.round(defaultAmount / 100)),
      payment_method: "cash" as const,
      reference_number: "",
      notes: "",
    },
  });

  // Reset form when modal opens with fresh defaults
  React.useEffect(() => {
    if (open) {
      const amt = prefillAmount ?? invoice.balance;
      reset({
        amount_display: String(Math.round(amt / 100)),
        payment_method: "cash",
        reference_number: "",
        notes: "",
      });
    }
  }, [open, invoice.balance, prefillAmount, reset]);

  const watchedMethod = watch("payment_method");
  const watchedAmount = watch("amount_display");

  // Live balance preview
  const enteredCents = (() => {
    const parsed = parseInt(watchedAmount || "0", 10);
    return isNaN(parsed) ? 0 : parsed * 100;
  })();
  const newBalance = Math.max(0, invoice.balance - enteredCents);

  const showReference = watchedMethod === "card" || watchedMethod === "transfer";

  function onSubmit(values: { amount_display: number; payment_method: "cash" | "card" | "transfer" | "other"; reference_number?: string | null; notes?: string | null }) {
    recordPayment(
      {
        amount: values.amount_display, // already transformed to cents by zod
        payment_method: values.payment_method,
        reference_number: values.reference_number || null,
        notes: values.notes || null,
      },
      {
        onSuccess: () => {
          onOpenChange(false);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Registrar Pago</DialogTitle>
          <DialogDescription>
            Factura {invoice.invoice_number}
          </DialogDescription>
        </DialogHeader>

        {/* Invoice summary bar */}
        <div className="flex flex-wrap gap-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.3)] p-3 text-sm">
          <div>
            <span className="text-[hsl(var(--muted-foreground))]">Total: </span>
            <span className="font-semibold tabular-nums">
              {formatCurrency(invoice.total, "COP")}
            </span>
          </div>
          <div>
            <span className="text-[hsl(var(--muted-foreground))]">Pagado: </span>
            <span className="font-semibold tabular-nums text-green-600">
              {formatCurrency(invoice.amount_paid, "COP")}
            </span>
          </div>
          <div>
            <span className="text-[hsl(var(--muted-foreground))]">Saldo: </span>
            <span className="font-semibold tabular-nums text-orange-600">
              {formatCurrency(invoice.balance, "COP")}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Amount */}
          <div className="space-y-1.5">
            <label htmlFor="payment-amount" className="text-sm font-medium text-foreground">
              Monto (COP) <span className="text-destructive">*</span>
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[hsl(var(--muted-foreground))] pointer-events-none">
                $
              </span>
              <Input
                id="payment-amount"
                type="text"
                inputMode="numeric"
                className="pl-7 tabular-nums"
                {...register("amount_display")}
                disabled={isPending}
              />
            </div>
            {errors.amount_display && (
              <p className="text-xs text-destructive">{errors.amount_display.message}</p>
            )}
            {/* Live balance preview */}
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Saldo después del pago:{" "}
              <span className={newBalance === 0 ? "text-green-600 font-medium" : "text-orange-600 font-medium"}>
                {formatCurrency(newBalance, "COP")}
              </span>
            </p>
          </div>

          {/* Payment method */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">
              Método de pago <span className="text-destructive">*</span>
            </label>
            <Controller
              name="payment_method"
              control={control}
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={isPending}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar método" />
                  </SelectTrigger>
                  <SelectContent>
                    {PAYMENT_METHODS.map((method) => (
                      <SelectItem key={method} value={method}>
                        {PAYMENT_METHOD_LABELS[method]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.payment_method && (
              <p className="text-xs text-destructive">{errors.payment_method.message}</p>
            )}
          </div>

          {/* Reference number (conditional) */}
          {showReference && (
            <div className="space-y-1.5">
              <label htmlFor="payment-ref" className="text-sm font-medium text-foreground">
                Número de referencia
              </label>
              <Input
                id="payment-ref"
                placeholder="Ej. 12345678"
                {...register("reference_number")}
                disabled={isPending}
              />
              {errors.reference_number && (
                <p className="text-xs text-destructive">{errors.reference_number.message}</p>
              )}
            </div>
          )}

          {/* Notes */}
          <div className="space-y-1.5">
            <label htmlFor="payment-notes" className="text-sm font-medium text-foreground">
              Notas
            </label>
            <textarea
              id="payment-notes"
              rows={2}
              placeholder="Observaciones del pago (opcional)"
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
              {...register("notes")}
              disabled={isPending}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending} className="min-w-[140px]">
              <DollarSign className="mr-1.5 h-3.5 w-3.5" />
              {isPending ? "Registrando..." : "Registrar pago"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
