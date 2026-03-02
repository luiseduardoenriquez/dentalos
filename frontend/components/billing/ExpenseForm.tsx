"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, ReceiptText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ExpenseCategory {
  id: string;
  name: string;
  description: string | null;
}

// ─── Validation Schema ────────────────────────────────────────────────────────

const expenseSchema = z.object({
  category_id: z.string().min(1, "Selecciona una categoría"),
  amount_display: z
    .string()
    .min(1, "Ingresa el monto")
    .regex(/^\d+(\.\d{0,2})?$/, "Monto inválido"),
  description: z
    .string()
    .min(3, "La descripción debe tener al menos 3 caracteres")
    .max(255, "Máximo 255 caracteres"),
  expense_date: z.string().min(1, "Selecciona una fecha"),
  receipt_url: z
    .string()
    .url("URL de recibo inválida")
    .optional()
    .or(z.literal("")),
  notes: z.string().max(500).optional().or(z.literal("")),
});

type ExpenseFormValues = z.infer<typeof expenseSchema>;

// ─── Component ────────────────────────────────────────────────────────────────

interface ExpenseFormProps {
  /** Called after successful submission. Defaults to router.push("/billing/expenses"). */
  onSuccess?: () => void;
  /** Default date (ISO string YYYY-MM-DD). Defaults to today. */
  defaultDate?: string;
}

export function ExpenseForm({ onSuccess, defaultDate }: ExpenseFormProps) {
  const router = useRouter();
  const [serverError, setServerError] = React.useState<string | null>(null);

  const today = new Date().toISOString().split("T")[0];

  // Fetch categories
  const { data: categories = [], isLoading: categoriesLoading } = useQuery({
    queryKey: ["expense-categories"],
    queryFn: () => apiGet<ExpenseCategory[]>("/expenses/categories"),
    staleTime: 5 * 60_000,
  });

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      category_id: "",
      amount_display: "",
      description: "",
      expense_date: defaultDate ?? today,
      receipt_url: "",
      notes: "",
    },
  });

  async function onSubmit(values: ExpenseFormValues) {
    setServerError(null);
    try {
      await apiPost("/expenses", {
        category_id: values.category_id,
        amount_cents: Math.round(parseFloat(values.amount_display) * 100),
        description: values.description,
        expense_date: values.expense_date,
        receipt_url: values.receipt_url || null,
        notes: values.notes || null,
      });
      if (onSuccess) {
        onSuccess();
      } else {
        router.push("/billing/expenses");
      }
    } catch {
      setServerError("No se pudo registrar el gasto. Intenta de nuevo.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {/* Server error */}
      {serverError && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300">
          {serverError}
        </div>
      )}

      {/* Category */}
      <div className="space-y-1.5">
        <Label htmlFor="expense-category">
          Categoría <span className="text-destructive">*</span>
        </Label>
        <Controller
          name="category_id"
          control={control}
          render={({ field }) => (
            <Select
              value={field.value}
              onValueChange={field.onChange}
              disabled={isSubmitting || categoriesLoading}
            >
              <SelectTrigger
                id="expense-category"
                className={cn(errors.category_id && "border-destructive")}
              >
                <SelectValue
                  placeholder={
                    categoriesLoading ? "Cargando categorías..." : "Seleccionar categoría"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {categories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.id}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.category_id && (
          <p className="text-xs text-destructive">{errors.category_id.message}</p>
        )}
      </div>

      {/* Amount */}
      <div className="space-y-1.5">
        <Label htmlFor="expense-amount">
          Monto (COP) <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[hsl(var(--muted-foreground))] pointer-events-none select-none">
            $
          </span>
          <Input
            id="expense-amount"
            type="text"
            inputMode="decimal"
            placeholder="0"
            className={cn("pl-7 tabular-nums", errors.amount_display && "border-destructive")}
            {...register("amount_display")}
            disabled={isSubmitting}
          />
        </div>
        {errors.amount_display && (
          <p className="text-xs text-destructive">{errors.amount_display.message}</p>
        )}
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <Label htmlFor="expense-description">
          Descripción <span className="text-destructive">*</span>
        </Label>
        <Input
          id="expense-description"
          placeholder="Ej. Compra de guantes de látex"
          className={cn(errors.description && "border-destructive")}
          {...register("description")}
          disabled={isSubmitting}
        />
        {errors.description && (
          <p className="text-xs text-destructive">{errors.description.message}</p>
        )}
      </div>

      {/* Date */}
      <div className="space-y-1.5">
        <Label htmlFor="expense-date">
          Fecha del gasto <span className="text-destructive">*</span>
        </Label>
        <Input
          id="expense-date"
          type="date"
          max={today}
          className={cn("w-40", errors.expense_date && "border-destructive")}
          {...register("expense_date")}
          disabled={isSubmitting}
        />
        {errors.expense_date && (
          <p className="text-xs text-destructive">{errors.expense_date.message}</p>
        )}
      </div>

      {/* Receipt URL (optional) */}
      <div className="space-y-1.5">
        <Label htmlFor="expense-receipt">
          URL del recibo{" "}
          <span className="text-[hsl(var(--muted-foreground))] font-normal text-xs">
            (opcional)
          </span>
        </Label>
        <Input
          id="expense-receipt"
          type="url"
          placeholder="https://..."
          className={cn(errors.receipt_url && "border-destructive")}
          {...register("receipt_url")}
          disabled={isSubmitting}
        />
        {errors.receipt_url && (
          <p className="text-xs text-destructive">{errors.receipt_url.message}</p>
        )}
      </div>

      {/* Notes (optional) */}
      <div className="space-y-1.5">
        <Label htmlFor="expense-notes">
          Notas{" "}
          <span className="text-[hsl(var(--muted-foreground))] font-normal text-xs">
            (opcional)
          </span>
        </Label>
        <textarea
          id="expense-notes"
          rows={2}
          placeholder="Observaciones adicionales"
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
          {...register("notes")}
          disabled={isSubmitting}
        />
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push("/billing/expenses")}
          disabled={isSubmitting}
        >
          Cancelar
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Guardando...
            </>
          ) : (
            <>
              <ReceiptText className="mr-2 h-4 w-4" />
              Registrar gasto
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
