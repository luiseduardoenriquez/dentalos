"use client";

import * as React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CalendarDays } from "lucide-react";
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
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { useCreatePaymentPlan } from "@/lib/hooks/use-payments";
import type { InvoiceResponse } from "@/lib/hooks/use-invoices";
import {
  paymentPlanCreateSchema,
  PAYMENT_PLAN_FREQUENCIES,
  FREQUENCY_LABELS,
} from "@/lib/validations/payment-plan";
import { formatCurrency, formatDate } from "@/lib/utils";

interface PaymentPlanModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  patientId: string;
  invoice: InvoiceResponse;
}

function generatePreviewSchedule(
  balance: number,
  numInstallments: number,
  frequency: string,
  startDate: string,
): Array<{ number: number; date: string; amount: number }> {
  if (!numInstallments || numInstallments < 2 || !startDate) return [];

  const baseAmount = Math.floor(balance / numInstallments);
  const remainder = balance - baseAmount * numInstallments;

  const schedule: Array<{ number: number; date: string; amount: number }> = [];
  const start = new Date(startDate + "T12:00:00");

  for (let i = 0; i < numInstallments; i++) {
    const date = new Date(start);
    if (frequency === "weekly") {
      date.setDate(date.getDate() + i * 7);
    } else if (frequency === "biweekly") {
      date.setDate(date.getDate() + i * 14);
    } else {
      date.setMonth(date.getMonth() + i);
    }

    schedule.push({
      number: i + 1,
      date: date.toISOString().split("T")[0],
      amount: i === 0 ? baseAmount + remainder : baseAmount,
    });
  }

  return schedule;
}

export function PaymentPlanModal({
  open,
  onOpenChange,
  patientId,
  invoice,
}: PaymentPlanModalProps) {
  const { mutate: createPlan, isPending } = useCreatePaymentPlan(
    patientId,
    invoice.id,
  );

  const [frequency, setFrequency] = React.useState<string>("monthly");

  const today = new Date().toISOString().split("T")[0];

  const {
    register,
    handleSubmit,
    watch,
    reset,
    control,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(paymentPlanCreateSchema),
    defaultValues: {
      num_installments: 3,
      first_due_date: today,
    },
  });

  React.useEffect(() => {
    if (open) {
      reset({ num_installments: 3, first_due_date: today });
      setFrequency("monthly");
    }
  }, [open, reset, today]);

  const watchedInstallments = watch("num_installments");
  const watchedStartDate = watch("first_due_date");

  const preview = generatePreviewSchedule(
    invoice.balance,
    Number(watchedInstallments) || 0,
    frequency,
    watchedStartDate || today,
  );

  function onSubmit(values: { num_installments: number; first_due_date: string }) {
    createPlan(
      {
        num_installments: values.num_installments,
        first_due_date: values.first_due_date,
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
          <DialogTitle>Crear Plan de Pagos</DialogTitle>
          <DialogDescription>
            Factura {invoice.invoice_number} — Saldo:{" "}
            {formatCurrency(invoice.balance, "COP")}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {/* Number of installments */}
            <div className="space-y-1.5">
              <label htmlFor="num-installments" className="text-sm font-medium text-foreground">
                Número de cuotas <span className="text-destructive">*</span>
              </label>
              <Input
                id="num-installments"
                type="number"
                min={2}
                max={48}
                {...register("num_installments")}
                disabled={isPending}
              />
              {errors.num_installments && (
                <p className="text-xs text-destructive">
                  {errors.num_installments.message}
                </p>
              )}
            </div>

            {/* Frequency */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">
                Frecuencia
              </label>
              <Select value={frequency} onValueChange={setFrequency} disabled={isPending}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_PLAN_FREQUENCIES.map((freq) => (
                    <SelectItem key={freq} value={freq}>
                      {FREQUENCY_LABELS[freq]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Start date */}
            <div className="space-y-1.5">
              <label htmlFor="first-due-date" className="text-sm font-medium text-foreground">
                Fecha primera cuota <span className="text-destructive">*</span>
              </label>
              <Input
                id="first-due-date"
                type="date"
                min={today}
                {...register("first_due_date")}
                disabled={isPending}
              />
              {errors.first_due_date && (
                <p className="text-xs text-destructive">
                  {errors.first_due_date.message}
                </p>
              )}
            </div>
          </div>

          {/* Preview schedule */}
          {preview.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">
                Previsualización del plan
              </p>
              <div className="max-h-60 overflow-y-auto rounded-md border border-[hsl(var(--border))]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[60px]">#</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead className="text-right">Monto</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.map((item) => (
                      <TableRow key={item.number}>
                        <TableCell className="text-sm tabular-nums">
                          {item.number}
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatDate(item.date)}
                        </TableCell>
                        <TableCell className="text-right text-sm font-medium tabular-nums">
                          {formatCurrency(item.amount, "COP")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

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
              <CalendarDays className="mr-1.5 h-3.5 w-3.5" />
              {isPending ? "Creando..." : "Crear plan"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
