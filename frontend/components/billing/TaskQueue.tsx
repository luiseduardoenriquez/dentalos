"use client";

import * as React from "react";
import Link from "next/link";
import { CheckCircle2, Clock, PlayCircle, XCircle, AlertTriangle, User } from "lucide-react";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiPut } from "@/lib/api-client";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type TaskType = "delinquency" | "acceptance" | "manual";
export type TaskStatus = "pending" | "in_progress" | "completed" | "discarded";
export type TaskPriority = "low" | "normal" | "high" | "urgent";

export interface Task {
  id: string;
  title: string;
  type: TaskType;
  status: TaskStatus;
  priority: TaskPriority;
  patient_id: string | null;
  patient_name: string | null;
  due_date: string | null;
  notes: string | null;
  created_at: string;
  assigned_to_name: string | null;
}

interface TaskQueueProps {
  tasks: Task[];
  loading?: boolean;
  /** React Query key prefix to invalidate after status change */
  queryKey?: unknown[];
  emptyMessage?: string;
}

// ─── Label Maps ───────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<TaskType, string> = {
  delinquency: "Morosidad",
  acceptance: "Aceptación",
  manual: "Manual",
};

const TYPE_BADGE_CLASS: Record<TaskType, string> = {
  delinquency:
    "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  acceptance:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  manual:
    "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

const STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "Pendiente",
  in_progress: "En progreso",
  completed: "Completada",
  discarded: "Descartada",
};

const STATUS_BADGE_VARIANT: Record<
  TaskStatus,
  "default" | "secondary" | "success" | "destructive"
> = {
  pending: "secondary",
  in_progress: "default",
  completed: "success",
  discarded: "destructive",
};

const PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Baja",
  normal: "Normal",
  high: "Alta",
  urgent: "Urgente",
};

const PRIORITY_CLASS: Record<TaskPriority, string> = {
  low: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  normal: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  high: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  urgent:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 font-semibold",
};

// ─── Status Mutation Hook ─────────────────────────────────────────────────────

function useUpdateTaskStatus(queryKey: unknown[]) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      status,
    }: {
      taskId: string;
      status: TaskStatus;
    }) => apiPut(`/tasks/${taskId}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

// ─── Action Buttons ───────────────────────────────────────────────────────────

function TaskActions({
  task,
  onStatusChange,
  isPending,
}: {
  task: Task;
  onStatusChange: (taskId: string, status: TaskStatus) => void;
  isPending: boolean;
}) {
  const { status } = task;

  if (status === "completed" || status === "discarded") {
    return (
      <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>
    );
  }

  return (
    <div className="flex items-center gap-1.5 justify-end">
      {status === "pending" && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 text-xs text-blue-600 border-blue-200 hover:bg-blue-50"
          onClick={() => onStatusChange(task.id, "in_progress")}
          disabled={isPending}
          title="Marcar en progreso"
        >
          <PlayCircle className="h-3.5 w-3.5 mr-1" />
          Iniciar
        </Button>
      )}
      {(status === "pending" || status === "in_progress") && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 text-xs text-green-600 border-green-200 hover:bg-green-50"
          onClick={() => onStatusChange(task.id, "completed")}
          disabled={isPending}
          title="Marcar como completada"
        >
          <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
          Completar
        </Button>
      )}
      <Button
        size="sm"
        variant="ghost"
        className="h-7 px-2 text-xs text-[hsl(var(--muted-foreground))] hover:text-destructive"
        onClick={() => onStatusChange(task.id, "discarded")}
        disabled={isPending}
        title="Descartar tarea"
      >
        <XCircle className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TaskSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i} className="hover:bg-transparent">
          <TableCell><Skeleton className="h-4 w-48" /></TableCell>
          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
          <TableCell><Skeleton className="h-7 w-28 ml-auto" /></TableCell>
        </TableRow>
      ))}
    </>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function TaskQueue({
  tasks,
  loading = false,
  queryKey = ["tasks"],
  emptyMessage = "No hay tareas en la cola.",
}: TaskQueueProps) {
  const { mutate: updateStatus, isPending } = useUpdateTaskStatus(queryKey);

  function handleStatusChange(taskId: string, status: TaskStatus) {
    updateStatus({ taskId, status });
  }

  const isOverdue = (dueDate: string | null) => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date();
  };

  return (
    <TableWrapper>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Título</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Paciente</TableHead>
            <TableHead>Prioridad</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead>Vencimiento</TableHead>
            <TableHead className="text-right">Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <TaskSkeleton />
          ) : tasks.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={7}
                className="h-28 text-center text-sm text-[hsl(var(--muted-foreground))]"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            tasks.map((task) => (
              <TableRow
                key={task.id}
                className={cn(
                  task.status === "completed" && "opacity-60",
                  task.status === "discarded" && "opacity-40 line-through",
                )}
              >
                {/* Title */}
                <TableCell className="max-w-[220px]">
                  <p className="text-sm font-medium text-foreground truncate">
                    {task.title}
                  </p>
                  {task.assigned_to_name && (
                    <p className="text-[11px] text-[hsl(var(--muted-foreground))] flex items-center gap-1 mt-0.5">
                      <User className="h-3 w-3" />
                      {task.assigned_to_name}
                    </p>
                  )}
                </TableCell>

                {/* Type badge */}
                <TableCell>
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                      TYPE_BADGE_CLASS[task.type],
                    )}
                  >
                    {TYPE_LABELS[task.type]}
                  </span>
                </TableCell>

                {/* Patient */}
                <TableCell>
                  {task.patient_id && task.patient_name ? (
                    <Link
                      href={`/patients/${task.patient_id}`}
                      className="text-sm text-primary-600 hover:text-primary-700 hover:underline"
                    >
                      {task.patient_name}
                    </Link>
                  ) : (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">—</span>
                  )}
                </TableCell>

                {/* Priority badge */}
                <TableCell>
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2 py-0.5 text-xs",
                      PRIORITY_CLASS[task.priority],
                    )}
                  >
                    {task.priority === "urgent" && (
                      <AlertTriangle className="h-3 w-3 mr-1" />
                    )}
                    {PRIORITY_LABELS[task.priority]}
                  </span>
                </TableCell>

                {/* Status badge */}
                <TableCell>
                  <Badge
                    variant={STATUS_BADGE_VARIANT[task.status]}
                    className="text-xs"
                  >
                    {STATUS_LABELS[task.status]}
                  </Badge>
                </TableCell>

                {/* Due date */}
                <TableCell>
                  {task.due_date ? (
                    <span
                      className={cn(
                        "text-sm tabular-nums flex items-center gap-1",
                        isOverdue(task.due_date) &&
                          task.status !== "completed" &&
                          task.status !== "discarded" &&
                          "text-red-600 font-medium",
                      )}
                    >
                      {isOverdue(task.due_date) &&
                        task.status !== "completed" &&
                        task.status !== "discarded" && (
                          <Clock className="h-3.5 w-3.5" />
                        )}
                      {formatDate(task.due_date)}
                    </span>
                  ) : (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">—</span>
                  )}
                </TableCell>

                {/* Actions */}
                <TableCell>
                  <TaskActions
                    task={task}
                    onStatusChange={handleStatusChange}
                    isPending={isPending}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableWrapper>
  );
}
