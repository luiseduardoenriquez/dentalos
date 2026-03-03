"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiPost, apiGet } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface QuickAddTaskButtonProps {
  context: "patient" | "invoice" | "appointment";
  referenceId: string;
  patientId?: string;
  className?: string;
}

type TaskPriority = "low" | "normal" | "high" | "urgent";

interface StaffMember {
  id: string;
  full_name: string;
}

interface TaskCreatePayload {
  title: string;
  priority: TaskPriority;
  assigned_to_id?: string;
  task_type: "manual";
  reference_id: string;
  reference_type: "patient" | "invoice" | "appointment";
  patient_id?: string;
}

// ─── Priority config ──────────────────────────────────────────────────────────

const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: "low", label: "Baja" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function QuickAddTaskButton({
  context,
  referenceId,
  patientId,
  className,
}: QuickAddTaskButtonProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [priority, setPriority] = React.useState<TaskPriority>("normal");
  const [assignedToId, setAssignedToId] = React.useState<string>("");

  const { data: staff } = useQuery({
    queryKey: ["staff", "list"],
    queryFn: () => apiGet<StaffMember[]>("/users?role=staff"),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  const { mutate: createTask, isPending } = useMutation({
    mutationFn: (payload: TaskCreatePayload) =>
      apiPost<void>("/tasks", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setTitle("");
      setPriority("normal");
      setAssignedToId("");
      setOpen(false);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    createTask({
      title: title.trim(),
      priority,
      assigned_to_id: assignedToId || undefined,
      task_type: "manual",
      reference_id: referenceId,
      reference_type: context,
      patient_id: patientId,
    });
  }

  const contextLabels: Record<QuickAddTaskButtonProps["context"], string> = {
    patient: "paciente",
    invoice: "factura",
    appointment: "cita",
  };

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className={cn("h-7 gap-1.5 px-2 text-xs", className)}
        title={`Agregar tarea para este ${contextLabels[context]}`}
      >
        <Plus className="h-3 w-3" />
        Tarea
      </Button>

      <Dialog open={open} onOpenChange={(v) => !v && setOpen(false)}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Nueva tarea</DialogTitle>
            <DialogDescription>
              Crea una tarea vinculada a este{" "}
              <span className="font-medium">{contextLabels[context]}</span>.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Title */}
            <div className="space-y-1.5">
              <Label htmlFor="task-title">Título de la tarea</Label>
              <Input
                id="task-title"
                placeholder="Ej: Llamar al paciente para confirmar..."
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                autoFocus
              />
            </div>

            {/* Priority */}
            <div className="space-y-1.5">
              <Label htmlFor="task-priority">Prioridad</Label>
              <div className="flex gap-2 flex-wrap">
                {PRIORITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setPriority(opt.value)}
                    className={cn(
                      "rounded-md px-3 py-1.5 text-xs font-medium border transition-colors",
                      priority === opt.value
                        ? opt.value === "urgent"
                          ? "bg-red-100 text-red-700 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700"
                          : opt.value === "high"
                            ? "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-700"
                            : opt.value === "normal"
                              ? "bg-primary-100 text-primary-700 border-primary-300 dark:bg-primary-900/30 dark:text-primary-300 dark:border-primary-700"
                              : "bg-slate-100 text-slate-700 border-slate-300 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-600"
                        : "bg-transparent text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]",
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Assign to */}
            <div className="space-y-1.5">
              <Label htmlFor="task-assign">
                Asignar a{" "}
                <span className="text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </Label>
              <select
                id="task-assign"
                value={assignedToId}
                onChange={(e) => setAssignedToId(e.target.value)}
                className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary-600"
              >
                <option value="">Sin asignar</option>
                {(staff ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name}
                  </option>
                ))}
              </select>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={isPending}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={isPending || !title.trim()}>
                {isPending ? "Guardando..." : "Crear tarea"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
