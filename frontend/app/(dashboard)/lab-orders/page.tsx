"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FlaskConical,
  Plus,
  AlertTriangle,
  LayoutGrid,
  List,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Pagination } from "@/components/pagination";
import { LabOrdersKanban } from "@/components/lab-orders/lab-orders-kanban";
import { LabOrderStatusBadge } from "@/components/lab-orders/lab-order-status-badge";
import {
  useLabOrders,
  useDentalLabs,
  useOverdueLabOrders,
} from "@/lib/hooks/use-lab-orders";
import { formatDate, formatCurrency } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 50;

const STATUS_OPTIONS = [
  { value: "all", label: "Todos los estados" },
  { value: "pending", label: "Pendiente" },
  { value: "sent_to_lab", label: "Enviada al lab" },
  { value: "in_progress", label: "En proceso" },
  { value: "ready", label: "Lista" },
  { value: "delivered", label: "Entregada" },
  { value: "cancelled", label: "Cancelada" },
];

const ORDER_TYPE_LABELS: Record<string, string> = {
  corona: "Corona",
  puente: "Puente",
  protesis: "Prótesis",
  abutment_implante: "Abutment implante",
  retenedor: "Retenedor",
  otro: "Otro",
};

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-9 w-48" />
      </div>
      <div className="flex gap-3 overflow-hidden">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-64 min-w-[220px] rounded-lg" />
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LabOrdersPage() {
  const router = useRouter();
  const [page, setPage] = React.useState(1);
  const [statusFilter, setStatusFilter] = React.useState("all");
  const [labFilter, setLabFilter] = React.useState("all");
  const [viewMode, setViewMode] = React.useState<"kanban" | "table">("kanban");

  const { data: labsData, isLoading: labsLoading } = useDentalLabs();
  const { data: overdueOrders } = useOverdueLabOrders();

  const { data, isLoading: ordersLoading } = useLabOrders(
    page,
    PAGE_SIZE,
    statusFilter !== "all" ? statusFilter : undefined,
    labFilter !== "all" ? labFilter : undefined,
  );

  const labs = labsData ?? [];
  const orders = data?.items ?? [];
  const total = data?.total ?? 0;
  const overdueCount = overdueOrders?.length ?? 0;

  const isLoading = labsLoading || (ordersLoading && !data);

  const labMap = React.useMemo(
    () =>
      labs.reduce<Record<string, string>>((acc, lab) => {
        acc[lab.id] = lab.name;
        return acc;
      }, {}),
    [labs],
  );

  if (isLoading) {
    return <PageSkeleton />;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Órdenes de laboratorio
          </h1>
        </div>
        <Button asChild>
          <Link href="/lab-orders/new">
            <Plus className="mr-1.5 h-4 w-4" />
            Nueva orden
          </Link>
        </Button>
      </div>

      {/* Overdue alert */}
      {overdueCount > 0 && (
        <Card className="border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800">
          <CardContent className="flex items-center gap-3 py-3 px-4">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0" />
            <p className="text-sm font-medium text-red-700 dark:text-red-300">
              {overdueCount === 1
                ? "Hay 1 orden vencida sin entregar."
                : `Hay ${overdueCount} órdenes vencidas sin entregar.`}{" "}
              Revisa el estado de las órdenes pendientes.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Filters + view toggle */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status filter */}
        <div className="space-y-1">
          <label
            htmlFor="lab-status-filter"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Estado
          </label>
          <Select
            value={statusFilter}
            onValueChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
          >
            <SelectTrigger id="lab-status-filter" className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Lab filter */}
        <div className="space-y-1">
          <label
            htmlFor="lab-lab-filter"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Laboratorio
          </label>
          <Select
            value={labFilter}
            onValueChange={(v) => {
              setLabFilter(v);
              setPage(1);
            }}
          >
            <SelectTrigger id="lab-lab-filter" className="w-48">
              <SelectValue placeholder="Todos los labs" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los laboratorios</SelectItem>
              {labs.map((lab) => (
                <SelectItem key={lab.id} value={lab.id}>
                  {lab.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* View toggle */}
        <div className="ml-auto flex items-end gap-1">
          <Button
            variant={viewMode === "kanban" ? "default" : "outline"}
            size="icon"
            className="h-9 w-9"
            onClick={() => setViewMode("kanban")}
            title="Vista kanban"
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "table" ? "default" : "outline"}
            size="icon"
            className="h-9 w-9"
            onClick={() => setViewMode("table")}
            title="Vista tabla"
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Count */}
      {total > 0 && (
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {total} orden{total !== 1 ? "es" : ""}
        </p>
      )}

      {/* Kanban view */}
      {viewMode === "kanban" && (
        <LabOrdersKanban
          orders={orders}
          labs={labs}
          onOrderClick={(id) => router.push(`/lab-orders/${id}`)}
        />
      )}

      {/* Table view */}
      {viewMode === "table" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              {total > 0
                ? `${total} orden${total !== 1 ? "es" : ""}`
                : "Órdenes"}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Tipo</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Laboratorio</TableHead>
                    <TableHead>Fecha de entrega</TableHead>
                    <TableHead className="text-right">Costo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ordersLoading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                      <TableRow key={i} className="hover:bg-transparent">
                        <TableCell>
                          <Skeleton className="h-4 w-28" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-5 w-24" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-4 w-32" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-4 w-24" />
                        </TableCell>
                        <TableCell>
                          <Skeleton className="h-4 w-20 ml-auto" />
                        </TableCell>
                      </TableRow>
                    ))
                  ) : orders.length === 0 ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell
                        colSpan={5}
                        className="h-32 text-center text-sm text-[hsl(var(--muted-foreground))]"
                      >
                        No hay órdenes para los filtros seleccionados.
                      </TableCell>
                    </TableRow>
                  ) : (
                    orders.map((order) => {
                      const today = new Date();
                      today.setHours(0, 0, 0, 0);
                      const isOverdue =
                        order.due_date != null &&
                        !["delivered", "cancelled"].includes(order.status) &&
                        new Date(order.due_date) < today;

                      return (
                        <TableRow
                          key={order.id}
                          className="cursor-pointer"
                          onClick={() => router.push(`/lab-orders/${order.id}`)}
                        >
                          <TableCell className="text-sm font-medium">
                            {ORDER_TYPE_LABELS[order.order_type] ?? order.order_type}
                          </TableCell>
                          <TableCell>
                            <LabOrderStatusBadge status={order.status} />
                          </TableCell>
                          <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                            {order.lab_id ? (labMap[order.lab_id] ?? "—") : "—"}
                          </TableCell>
                          <TableCell
                            className={
                              isOverdue
                                ? "text-sm font-medium text-red-600 dark:text-red-400"
                                : "text-sm text-[hsl(var(--muted-foreground))]"
                            }
                          >
                            {order.due_date ? formatDate(order.due_date) : "—"}
                          </TableCell>
                          <TableCell className="text-right text-sm tabular-nums">
                            {order.cost_cents != null
                              ? formatCurrency(order.cost_cents, "COP")
                              : "—"}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

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
