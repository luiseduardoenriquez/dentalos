"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ClipboardList,
  Plus,
  MoreHorizontal,
  Pencil,
  Archive,
  Copy,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface IntakeTemplate {
  id: string;
  name: string;
  description: string | null;
  field_count: number;
  is_active: boolean;
  response_count: number;
  created_at: string;
  public_url: string | null;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function IntakeTemplatesPage() {
  const queryClient = useQueryClient();

  const { data: templates, isLoading, isError } = useQuery({
    queryKey: ["settings", "intake-templates"],
    queryFn: () => apiGet<IntakeTemplate[]>("/intake/templates"),
    staleTime: 60_000,
  });

  const { mutate: createTemplate, isPending: isCreating } = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      apiPost("/intake/templates", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "intake-templates"] });
      setDialogOpen(false);
      setForm({ name: "", description: "" });
    },
  });

  const { mutate: toggleActive } = useMutation({
    mutationFn: (id: string) => apiPut(`/intake/templates/${id}/toggle-active`, {}),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["settings", "intake-templates"] }),
  });

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<IntakeTemplate | null>(null);
  const [form, setForm] = React.useState({ name: "", description: "" });

  function handleSave() {
    if (!form.name.trim()) return;
    createTemplate({ name: form.name.trim(), description: form.description.trim() });
  }

  function copyPublicUrl(url: string) {
    navigator.clipboard.writeText(url).catch(() => {});
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-9 w-36" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))] py-10 justify-center">
        <AlertCircle className="h-4 w-4 text-orange-500" />
        No se pudieron cargar los formularios de ingreso.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Formularios de ingreso
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Crea formularios públicos para recopilar datos de nuevos pacientes.
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo formulario
        </Button>
      </div>

      {/* Template list */}
      {!templates || templates.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-14 gap-3">
            <ClipboardList className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-50" />
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center">
              No hay formularios de ingreso creados.
              <br />
              Crea el primero para compartir con nuevos pacientes.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Crear formulario
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {templates.map((tpl) => (
            <div
              key={tpl.id}
              className={cn(
                "flex items-center justify-between rounded-lg border p-4 gap-4",
                !tpl.is_active && "opacity-60",
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-foreground">{tpl.name}</span>
                  {!tpl.is_active && (
                    <Badge variant="secondary" className="text-xs">
                      Archivado
                    </Badge>
                  )}
                </div>
                {tpl.description && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5 truncate">
                    {tpl.description}
                  </p>
                )}
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
                  {tpl.field_count} campos · {tpl.response_count} respuestas ·{" "}
                  {formatDate(tpl.created_at)}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {tpl.public_url && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyPublicUrl(tpl.public_url!)}
                    title="Copiar enlace público"
                  >
                    <Copy className="h-3.5 w-3.5 mr-1" />
                    Enlace
                  </Button>
                )}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                      <MoreHorizontal className="h-4 w-4" />
                      <span className="sr-only">Acciones</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => {
                        setEditTarget(tpl);
                        setForm({ name: tpl.name, description: tpl.description ?? "" });
                        setDialogOpen(true);
                      }}
                    >
                      <Pencil className="mr-2 h-3.5 w-3.5" />
                      Editar
                    </DropdownMenuItem>
                    {tpl.public_url && (
                      <DropdownMenuItem asChild>
                        <a href={tpl.public_url} target="_blank" rel="noreferrer">
                          <ExternalLink className="mr-2 h-3.5 w-3.5" />
                          Ver formulario
                        </a>
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem onClick={() => toggleActive(tpl.id)}>
                      <Archive className="mr-2 h-3.5 w-3.5" />
                      {tpl.is_active ? "Archivar" : "Reactivar"}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create dialog */}
      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            setEditTarget(null);
            setForm({ name: "", description: "" });
          }
          setDialogOpen(open);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editTarget ? "Editar formulario" : "Nuevo formulario de ingreso"}
            </DialogTitle>
            <DialogDescription>
              Define el nombre del formulario. Luego podrás agregar campos desde el editor.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <Label htmlFor="tpl-name">Nombre *</Label>
              <Input
                id="tpl-name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Ej: Ficha de ingreso adultos"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="tpl-desc">Descripción</Label>
              <Input
                id="tpl-desc"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Descripción breve del formulario"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={isCreating}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleSave}
              disabled={isCreating || !form.name.trim()}
            >
              {isCreating ? "Guardando..." : editTarget ? "Guardar cambios" : "Crear formulario"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
