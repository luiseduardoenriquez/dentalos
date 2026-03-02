"use client";

import * as React from "react";
import Link from "next/link";
import {
  ReceiptText,
  Plus,
  ExternalLink,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Pagination } from "@/components/pagination";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ExpenseCategory {
  id: string;
  name: string;
}

interface Expense {
  id: string;
  category_id: string;
  category_name: string;
  amount_cents: number;
  description: string;
  expense_date: string;
  receipt_url: string | null;
  notes: string | null;
  created_by_name: string;
  created_at: string;
}

interface ExpenseListResponse {
  items: Expense[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function ExpensesSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-9 w-40" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-9 w-36" />
        <Skeleton className="h-9 w-36" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

// ─── Table Skeleton ───────────────────────────────────────────────────────────

function TableRowSkeleton() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableRow key={i} className="hover:bg-transparent">
          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
          <TableCell><Skeleton className="h-4 w-48" /></TableCell>
          <TableCell><Skeleton className="h-4 w-24 ml-auto" /></TableCell>
          <TableCell><Skeleton className="h-4 w-8" /></TableCell>
        </TableRow>
      ))}
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function ExpensesPage() {
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .split("T")[0];
  const today = now.toISOString().split("T")[0];

  const [page, setPage] = React.useState(1);
  const [categoryId, setCategoryId] = React.useState<string>("all");
  const [dateFrom, setDateFrom] = React.useState(firstDay);
  const [dateTo, setDateTo] = React.useState(today);

  // Fetch categories for the filter dropdown
  const { data: categories = [] } = useQuery({
    queryKey: ["expense-categories"],
    queryFn: () => apiGet<ExpenseCategory[]>("/expenses/categories"),
    staleTime: 5 * 60_000,
  });

  // Fetch expenses
  const { data, isLoading } = useQuery({
    queryKey: ["expenses", { page, categoryId, dateFrom, dateTo }],
    queryFn: () =>
      apiGet<ExpenseListResponse>("/expenses", {
        page,
        page_size: PAGE_SIZE,
        category_id: categoryId !== "all" ? categoryId : undefined,
        date_from: dateFrom,
        date_to: dateTo,
      }),
    staleTime: 30_000,
  });

  if (isLoading && !data) {
    return (
      <div className="p-6">
        <ExpensesSkeleton />
      </div>
    );
  }

  const expenses = data?.items ?? [];
  const total = data?.total ?? 0;

  // Total for current filter period
  const periodTotal = expenses.reduce((sum, e) => sum + e.amount_cents, 0);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ReceiptText className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">Gastos</h1>
        </div>
        <Button asChild>
          <Link href="/billing/expenses/new">
            <Plus className="mr-1.5 h-4 w-4" />
            Nuevo gasto
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label
            htmlFor="exp-category"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Categoría
          </label>
          <Select
            value={categoryId}
            onValueChange={(v) => {
              setCategoryId(v);
              setPage(1);
            }}
          >
            <SelectTrigger id="exp-category" className="w-44">
              <SelectValue placeholder="Todas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las categorías</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.id} value={cat.id}>
                  {cat.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <label
            htmlFor="exp-date-from"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Desde
          </label>
          <Input
            id="exp-date-from"
            type="date"
            className="w-36"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-1">
          <label
            htmlFor="exp-date-to"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Hasta
          </label>
          <Input
            id="exp-date-to"
            type="date"
            className="w-36"
            max={today}
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
          />
        </div>

        {/* Period total */}
        {expenses.length > 0 && (
          <div className="ml-auto text-right">
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Total en filtro
            </p>
            <p className="text-base font-bold tabular-nums text-foreground">
              {formatCurrency(periodTotal, "COP")}
            </p>
          </div>
        )}
      </div>

      {/* Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">
            {total > 0 ? `${total} gasto${total !== 1 ? "s" : ""}` : "Gastos"}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <TableWrapper>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Fecha</TableHead>
                  <TableHead>Categoría</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead className="text-right">Monto</TableHead>
                  <TableHead className="text-right">Recibo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRowSkeleton />
                ) : expenses.length === 0 ? (
                  <TableRow className="hover:bg-transparent">
                    <TableCell
                      colSpan={5}
                      className="h-32 text-center text-sm text-[hsl(var(--muted-foreground))]"
                    >
                      No hay gastos registrados para este período.
                    </TableCell>
                  </TableRow>
                ) : (
                  expenses.map((expense) => (
                    <TableRow key={expense.id}>
                      <TableCell className="text-sm tabular-nums whitespace-nowrap text-[hsl(var(--muted-foreground))]">
                        {formatDate(expense.expense_date)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">
                          {expense.category_name}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[280px]">
                        <p className="text-sm text-foreground truncate">
                          {expense.description}
                        </p>
                        {expense.notes && (
                          <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">
                            {expense.notes}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className="text-sm font-semibold tabular-nums text-red-600 dark:text-red-400">
                          {formatCurrency(expense.amount_cents, "COP")}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        {expense.receipt_url ? (
                          <a
                            href={expense.receipt_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 hover:underline"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            Ver
                          </a>
                        ) : (
                          <span className="text-sm text-[hsl(var(--muted-foreground))]">
                            —
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableWrapper>
        </CardContent>
      </Card>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onChange={setPage}
        />
      )}
    </div>
  );
}
