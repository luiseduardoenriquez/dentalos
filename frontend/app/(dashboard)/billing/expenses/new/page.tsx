"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ExpenseForm } from "@/components/billing/ExpenseForm";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewExpensePage() {
  return (
    <div className="p-6 space-y-6 max-w-2xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href="/billing/expenses"
          className="flex items-center gap-1 text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Gastos
        </Link>
        <span className="text-[hsl(var(--muted-foreground))]">/</span>
        <span className="text-foreground font-medium">Nuevo gasto</span>
      </div>

      {/* Form card */}
      <Card>
        <CardHeader>
          <CardTitle>Registrar gasto</CardTitle>
          <CardDescription>
            Registra un gasto operativo de la clínica con su categoría y monto.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ExpenseForm />
        </CardContent>
      </Card>
    </div>
  );
}
