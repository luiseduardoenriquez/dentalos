"use client";

import * as React from "react";
import { ListTodo } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { TaskQueue, type TaskType, type TaskStatus } from "@/components/billing/TaskQueue";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface TaskListResponse {
  items: import("@/components/billing/TaskQueue").Task[];
  total: number;
}

// ─── Filter options ───────────────────────────────────────────────────────────

const TYPE_OPTIONS: { value: TaskType | "all"; label: string }[] = [
  { value: "all", label: "Todos los tipos" },
  { value: "delinquency", label: "Morosidad" },
  { value: "acceptance", label: "Aceptación" },
  { value: "manual", label: "Manual" },
];

const STATUS_OPTIONS: { value: TaskStatus | "active"; label: string }[] = [
  { value: "active", label: "Activas (pendiente + en progreso)" },
  { value: "pending", label: "Pendientes" },
  { value: "in_progress", label: "En progreso" },
  { value: "completed", label: "Completadas" },
  { value: "discarded", label: "Descartadas" },
];

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TasksSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-7 w-36" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-9 w-44" />
        <Skeleton className="h-9 w-48" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const QUERY_KEY = ["tasks"];

export default function TasksPage() {
  const [typeFilter, setTypeFilter] = React.useState<TaskType | "all">("all");
  const [statusFilter, setStatusFilter] = React.useState<TaskStatus | "active">("active");

  const { data, isLoading } = useQuery({
    queryKey: [...QUERY_KEY, { typeFilter, statusFilter }],
    queryFn: () =>
      apiGet<TaskListResponse>("/tasks", {
        type: typeFilter !== "all" ? typeFilter : undefined,
        status: statusFilter !== "active" ? statusFilter : undefined,
        active_only: statusFilter === "active" ? true : undefined,
        page_size: 100,
      }),
    staleTime: 30_000,
  });

  if (isLoading && !data) {
    return (
      <div className="p-6">
        <TasksSkeleton />
      </div>
    );
  }

  const tasks = data?.items ?? [];
  const total = data?.total ?? 0;

  const pendingCount = tasks.filter((t) => t.status === "pending").length;
  const inProgressCount = tasks.filter((t) => t.status === "in_progress").length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ListTodo className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Cola de tareas
          </h1>
        </div>

        {/* Quick counts */}
        {tasks.length > 0 && (
          <div className="flex items-center gap-4 text-sm text-[hsl(var(--muted-foreground))]">
            {pendingCount > 0 && (
              <span>
                <strong className="text-foreground">{pendingCount}</strong>{" "}
                pendiente{pendingCount !== 1 ? "s" : ""}
              </span>
            )}
            {inProgressCount > 0 && (
              <span>
                <strong className="text-blue-600">{inProgressCount}</strong>{" "}
                en progreso
              </span>
            )}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label
            htmlFor="task-type-filter"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Tipo
          </label>
          <Select
            value={typeFilter}
            onValueChange={(v) => setTypeFilter(v as TaskType | "all")}
          >
            <SelectTrigger id="task-type-filter" className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TYPE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label
            htmlFor="task-status-filter"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Estado
          </label>
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as TaskStatus | "active")}
          >
            <SelectTrigger id="task-status-filter" className="w-52">
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

        {total > 0 && (
          <p className="ml-auto text-xs text-[hsl(var(--muted-foreground))]">
            {total} tarea{total !== 1 ? "s" : ""} encontrada{total !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      {/* Task table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">Tareas</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <TaskQueue
            tasks={tasks}
            loading={isLoading}
            queryKey={[...QUERY_KEY, { typeFilter, statusFilter }]}
            emptyMessage={
              statusFilter === "active"
                ? "No hay tareas activas. La cola está limpia."
                : "No hay tareas para los filtros seleccionados."
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
