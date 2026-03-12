"use client";

import * as React from "react";
import {
  useAdminAnnouncements,
  useCreateAnnouncement,
  useUpdateAnnouncement,
  useDeleteAnnouncement,
  type AnnouncementResponse,
  type AnnouncementCreatePayload,
  type AnnouncementUpdatePayload,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  Megaphone,
  Plus,
  Pencil,
  Trash2,
  AlertCircle,
  Info,
  AlertTriangle,
} from "lucide-react";

// ─── Constants ─────────────────────────────────────────────────────────────────

const TYPE_OPTIONS = [
  { value: "info", label: "Informativo" },
  { value: "warning", label: "Advertencia" },
  { value: "critical", label: "Crítico" },
] as const;

const VISIBILITY_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "plan", label: "Por plan" },
  { value: "country", label: "Por país" },
] as const;

const TYPE_LABELS: Record<string, string> = {
  info: "Informativo",
  warning: "Advertencia",
  critical: "Crítico",
};

const VISIBILITY_LABELS: Record<string, string> = {
  all: "Todos",
  plan: "Por plan",
  country: "Por país",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function toDateInputValue(iso: string | null): string {
  if (!iso) return "";
  try {
    return iso.slice(0, 10);
  } catch {
    return "";
  }
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

// ─── Type Badge ────────────────────────────────────────────────────────────────

function AnnouncementTypeBadge({ type }: { type: string }) {
  if (type === "info") {
    return (
      <Badge
        variant="outline"
        className="border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300 text-xs gap-1"
      >
        <Info className="h-3 w-3" />
        {TYPE_LABELS[type] ?? type}
      </Badge>
    );
  }

  if (type === "warning") {
    return (
      <Badge
        variant="warning"
        className="text-xs gap-1"
      >
        <AlertTriangle className="h-3 w-3" />
        {TYPE_LABELS[type] ?? type}
      </Badge>
    );
  }

  if (type === "critical") {
    return (
      <Badge
        variant="destructive"
        className="text-xs gap-1"
      >
        <AlertCircle className="h-3 w-3" />
        {TYPE_LABELS[type] ?? type}
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="text-xs">
      {TYPE_LABELS[type] ?? type}
    </Badge>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function AnnouncementsLoadingSkeleton() {
  return (
    <Card>
      <CardContent className="p-0">
        <div className="divide-y divide-[hsl(var(--border))]">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-4 px-6 py-4">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-4 w-24 ml-auto" />
              <Skeleton className="h-8 w-8" />
              <Skeleton className="h-8 w-8" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Delete Confirmation Dialog ────────────────────────────────────────────────

interface DeleteConfirmDialogProps {
  announcement: AnnouncementResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function DeleteConfirmDialog({
  announcement,
  open,
  onOpenChange,
}: DeleteConfirmDialogProps) {
  const { success, error } = useToast();
  const deleteAnnouncement = useDeleteAnnouncement();

  function handleDelete() {
    deleteAnnouncement.mutate(announcement.id, {
      onSuccess: () => {
        success(
          "Anuncio eliminado",
          `"${announcement.title}" se eliminó correctamente.`,
        );
        onOpenChange(false);
      },
      onError: () => {
        error(
          "Error al eliminar",
          "No se pudo eliminar el anuncio. Intenta de nuevo.",
        );
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Eliminar anuncio</DialogTitle>
          <DialogDescription>
            Esta acción eliminará permanentemente el anuncio{" "}
            <strong>"{announcement.title}"</strong>. Los usuarios dejarán de
            verlo de inmediato. ¿Deseas continuar?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deleteAnnouncement.isPending}
          >
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteAnnouncement.isPending}
          >
            {deleteAnnouncement.isPending ? "Eliminando..." : "Eliminar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Announcement Form State ───────────────────────────────────────────────────

interface AnnouncementFormState {
  title: string;
  body: string;
  announcement_type: string;
  visibility: string;
  is_dismissable: boolean;
  starts_at: string;
  ends_at: string;
}

const EMPTY_FORM: AnnouncementFormState = {
  title: "",
  body: "",
  announcement_type: "info",
  visibility: "all",
  is_dismissable: true,
  starts_at: "",
  ends_at: "",
};

// ─── Announcement Form Fields ──────────────────────────────────────────────────
// Shared between create and edit dialogs.

interface AnnouncementFormFieldsProps {
  state: AnnouncementFormState;
  onChange: (updates: Partial<AnnouncementFormState>) => void;
}

function AnnouncementFormFields({
  state,
  onChange,
}: AnnouncementFormFieldsProps) {
  return (
    <div className="grid gap-4 py-2">
      {/* Titulo */}
      <div className="space-y-1.5">
        <Label htmlFor="ann-title">
          Título <span className="text-red-500">*</span>
        </Label>
        <Input
          id="ann-title"
          type="text"
          value={state.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="ej: Mantenimiento programado este viernes"
          className="text-sm"
        />
      </div>

      {/* Cuerpo */}
      <div className="space-y-1.5">
        <Label htmlFor="ann-body">
          Cuerpo <span className="text-red-500">*</span>
        </Label>
        <Textarea
          id="ann-body"
          rows={4}
          value={state.body}
          onChange={(e) => onChange({ body: e.target.value })}
          placeholder="Describe el contenido del anuncio que verán los usuarios..."
          className="resize-y text-sm"
        />
      </div>

      {/* Tipo */}
      <div className="space-y-1.5">
        <Label htmlFor="ann-type">Tipo</Label>
        <Select
          value={state.announcement_type}
          onValueChange={(val) => onChange({ announcement_type: val })}
        >
          <SelectTrigger id="ann-type" className="text-sm">
            <SelectValue placeholder="Selecciona un tipo" />
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

      {/* Visibilidad */}
      <div className="space-y-1.5">
        <Label htmlFor="ann-visibility">Visibilidad</Label>
        <Select
          value={state.visibility}
          onValueChange={(val) => onChange({ visibility: val })}
        >
          <SelectTrigger id="ann-visibility" className="text-sm">
            <SelectValue placeholder="Selecciona visibilidad" />
          </SelectTrigger>
          <SelectContent>
            {VISIBILITY_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          "Todos" muestra el anuncio a todas las clínicas de la plataforma.
        </p>
      </div>

      {/* Fechas */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="ann-starts-at">
            Fecha inicio{" "}
            <span className="text-[hsl(var(--muted-foreground))]">
              (opcional)
            </span>
          </Label>
          <Input
            id="ann-starts-at"
            type="date"
            value={state.starts_at}
            onChange={(e) => onChange({ starts_at: e.target.value })}
            className="text-sm"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ann-ends-at">
            Fecha fin{" "}
            <span className="text-[hsl(var(--muted-foreground))]">
              (opcional)
            </span>
          </Label>
          <Input
            id="ann-ends-at"
            type="date"
            value={state.ends_at}
            onChange={(e) => onChange({ ends_at: e.target.value })}
            className="text-sm"
          />
        </div>
      </div>

      {/* Descartable */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="ann-dismissable"
          checked={state.is_dismissable}
          onCheckedChange={(checked) =>
            onChange({ is_dismissable: checked === true })
          }
        />
        <Label htmlFor="ann-dismissable" className="cursor-pointer">
          Descartable
        </Label>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          — los usuarios pueden cerrar el anuncio manualmente
        </span>
      </div>
    </div>
  );
}

// ─── Create Announcement Dialog ────────────────────────────────────────────────

interface CreateAnnouncementDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function CreateAnnouncementDialog({
  open,
  onOpenChange,
}: CreateAnnouncementDialogProps) {
  const { success, error } = useToast();
  const createAnnouncement = useCreateAnnouncement();
  const [form, setForm] = React.useState<AnnouncementFormState>(EMPTY_FORM);

  React.useEffect(() => {
    if (open) setForm(EMPTY_FORM);
  }, [open]);

  const isValid = form.title.trim() !== "" && form.body.trim() !== "";

  function handleCreate() {
    if (!isValid) return;

    const payload: AnnouncementCreatePayload = {
      title: form.title.trim(),
      body: form.body.trim(),
      announcement_type: form.announcement_type,
      visibility: form.visibility,
      is_dismissable: form.is_dismissable,
      starts_at: form.starts_at.trim() || undefined,
      ends_at: form.ends_at.trim() || undefined,
    };

    createAnnouncement.mutate(payload, {
      onSuccess: () => {
        success(
          "Anuncio creado",
          `"${payload.title}" se publicó correctamente.`,
        );
        onOpenChange(false);
      },
      onError: () => {
        error(
          "Error al crear",
          "No se pudo crear el anuncio. Intenta de nuevo.",
        );
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Nuevo anuncio</DialogTitle>
          <DialogDescription>
            Los anuncios se muestran en el panel de todas las clínicas según la
            configuración de visibilidad.
          </DialogDescription>
        </DialogHeader>

        <AnnouncementFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createAnnouncement.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleCreate}
            disabled={createAnnouncement.isPending || !isValid}
          >
            {createAnnouncement.isPending ? "Publicando..." : "Publicar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Announcement Dialog ──────────────────────────────────────────────────

interface EditAnnouncementDialogProps {
  announcement: AnnouncementResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function EditAnnouncementDialog({
  announcement,
  open,
  onOpenChange,
}: EditAnnouncementDialogProps) {
  const { success, error } = useToast();
  const updateAnnouncement = useUpdateAnnouncement();

  const [form, setForm] = React.useState<AnnouncementFormState>({
    title: announcement.title,
    body: announcement.body,
    announcement_type: announcement.announcement_type,
    visibility: announcement.visibility,
    is_dismissable: announcement.is_dismissable,
    starts_at: toDateInputValue(announcement.starts_at),
    ends_at: toDateInputValue(announcement.ends_at),
  });

  // Sync form state when dialog opens with a (potentially different) announcement
  React.useEffect(() => {
    if (open) {
      setForm({
        title: announcement.title,
        body: announcement.body,
        announcement_type: announcement.announcement_type,
        visibility: announcement.visibility,
        is_dismissable: announcement.is_dismissable,
        starts_at: toDateInputValue(announcement.starts_at),
        ends_at: toDateInputValue(announcement.ends_at),
      });
    }
  }, [open, announcement]);

  const isValid = form.title.trim() !== "" && form.body.trim() !== "";

  function handleSave() {
    if (!isValid) return;

    const payload: AnnouncementUpdatePayload = {
      title: form.title.trim(),
      body: form.body.trim(),
      announcement_type: form.announcement_type,
      visibility: form.visibility,
      is_dismissable: form.is_dismissable,
      starts_at: form.starts_at.trim() || undefined,
      ends_at: form.ends_at.trim() || undefined,
    };

    updateAnnouncement.mutate(
      { id: announcement.id, payload },
      {
        onSuccess: () => {
          success(
            "Anuncio actualizado",
            "Los cambios se guardaron correctamente.",
          );
          onOpenChange(false);
        },
        onError: () => {
          error(
            "Error al guardar",
            "No se pudo actualizar el anuncio. Intenta de nuevo.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Editar anuncio</DialogTitle>
          <DialogDescription>
            Modifica el contenido y la configuración del anuncio. Los cambios
            serán visibles de inmediato.
          </DialogDescription>
        </DialogHeader>

        <AnnouncementFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updateAnnouncement.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            disabled={updateAnnouncement.isPending || !isValid}
          >
            {updateAnnouncement.isPending ? "Guardando..." : "Guardar cambios"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Toggle Active Row Action ──────────────────────────────────────────────────
// Inline toggle for is_active directly in the table row.

interface ToggleActiveButtonProps {
  announcement: AnnouncementResponse;
}

function ToggleActiveButton({ announcement }: ToggleActiveButtonProps) {
  const { success, error } = useToast();
  const updateAnnouncement = useUpdateAnnouncement();

  function handleToggle() {
    updateAnnouncement.mutate(
      {
        id: announcement.id,
        payload: { is_active: !announcement.is_active },
      },
      {
        onSuccess: () => {
          success(
            announcement.is_active ? "Anuncio desactivado" : "Anuncio activado",
            announcement.is_active
              ? "El anuncio ya no será visible para los usuarios."
              : "El anuncio es ahora visible para los usuarios.",
          );
        },
        onError: () => {
          error(
            "Error al actualizar",
            "No se pudo cambiar el estado del anuncio.",
          );
        },
      },
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleToggle}
      disabled={updateAnnouncement.isPending}
      className={cn(
        "text-xs h-7 px-2",
        announcement.is_active
          ? "text-[hsl(var(--muted-foreground))] hover:text-foreground"
          : "text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300",
      )}
    >
      {announcement.is_active ? "Desactivar" : "Activar"}
    </Button>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminAnnouncementsPage() {
  const { data, isLoading, isError, refetch } = useAdminAnnouncements();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editingAnnouncement, setEditingAnnouncement] =
    React.useState<AnnouncementResponse | null>(null);
  const [deletingAnnouncement, setDeletingAnnouncement] =
    React.useState<AnnouncementResponse | null>(null);

  const announcements = data?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Megaphone className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight">
              Anuncios de la Plataforma
            </h1>
          </div>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Publica mensajes informativos, advertencias y alertas críticas para
            los usuarios de todas las clínicas.
          </p>
        </div>
        <Button
          onClick={() => setCreateOpen(true)}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Nuevo Anuncio
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && <AnnouncementsLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <AlertCircle className="h-8 w-8 text-[hsl(var(--muted-foreground))]" />
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar los anuncios. Verifica la conexión con la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Announcements table */}
      {!isLoading && !isError && (
        <>
          {announcements.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
                <Megaphone className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-40" />
                <p className="text-[hsl(var(--muted-foreground))]">
                  No hay anuncios publicados. Crea el primero.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCreateOpen(true)}
                  className="gap-1"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Nuevo Anuncio
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader className="pb-0">
                <CardTitle className="text-base">
                  {data?.total ?? announcements.length}{" "}
                  {(data?.total ?? announcements.length) === 1
                    ? "anuncio en total"
                    : "anuncios en total"}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 mt-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="min-w-[200px]">Título</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Visibilidad</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead className="whitespace-nowrap">
                          Fecha inicio
                        </TableHead>
                        <TableHead className="whitespace-nowrap">
                          Fecha fin
                        </TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {announcements.map((announcement) => (
                        <TableRow key={announcement.id}>
                          {/* Titulo */}
                          <TableCell className="max-w-[240px]">
                            <div className="space-y-0.5">
                              <p
                                className="text-sm font-medium"
                                title={announcement.title}
                              >
                                {truncate(announcement.title, 50)}
                              </p>
                              {announcement.body && (
                                <p
                                  className="text-xs text-[hsl(var(--muted-foreground))]"
                                  title={announcement.body}
                                >
                                  {truncate(announcement.body, 70)}
                                </p>
                              )}
                            </div>
                          </TableCell>

                          {/* Tipo badge */}
                          <TableCell>
                            <AnnouncementTypeBadge
                              type={announcement.announcement_type}
                            />
                          </TableCell>

                          {/* Visibilidad */}
                          <TableCell>
                            <Badge
                              variant="outline"
                              className="border-slate-300 bg-slate-100 text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400 text-xs"
                            >
                              {VISIBILITY_LABELS[announcement.visibility] ??
                                announcement.visibility}
                            </Badge>
                          </TableCell>

                          {/* Estado (activo / inactivo) */}
                          <TableCell>
                            <Badge
                              variant={
                                announcement.is_active ? "success" : "secondary"
                              }
                            >
                              {announcement.is_active ? "Activo" : "Inactivo"}
                            </Badge>
                          </TableCell>

                          {/* Fecha inicio */}
                          <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                            {formatDate(announcement.starts_at)}
                          </TableCell>

                          {/* Fecha fin */}
                          <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                            {formatDate(announcement.ends_at)}
                          </TableCell>

                          {/* Acciones */}
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <ToggleActiveButton
                                announcement={announcement}
                              />
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-[hsl(var(--muted-foreground))] hover:text-foreground"
                                title="Editar anuncio"
                                onClick={() =>
                                  setEditingAnnouncement(announcement)
                                }
                              >
                                <Pencil className="h-3.5 w-3.5" />
                                <span className="sr-only">Editar</span>
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-[hsl(var(--muted-foreground))] hover:text-red-600 dark:hover:text-red-400"
                                title="Eliminar anuncio"
                                onClick={() =>
                                  setDeletingAnnouncement(announcement)
                                }
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                                <span className="sr-only">Eliminar</span>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Create dialog */}
      <CreateAnnouncementDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      {/* Edit dialog — only mounted when an announcement is selected */}
      {editingAnnouncement && (
        <EditAnnouncementDialog
          announcement={editingAnnouncement}
          open={editingAnnouncement !== null}
          onOpenChange={(open) => {
            if (!open) setEditingAnnouncement(null);
          }}
        />
      )}

      {/* Delete confirmation dialog — only mounted when an announcement is selected */}
      {deletingAnnouncement && (
        <DeleteConfirmDialog
          announcement={deletingAnnouncement}
          open={deletingAnnouncement !== null}
          onOpenChange={(open) => {
            if (!open) setDeletingAnnouncement(null);
          }}
        />
      )}
    </div>
  );
}
