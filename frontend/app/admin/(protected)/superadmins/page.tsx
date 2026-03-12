"use client";

/**
 * Admin superadmins management page.
 *
 * Full CRUD for superadmin accounts:
 * - Lists all superadmins with TOTP status, active state, last login, created date.
 * - Create dialog: name, email, password.
 * - Edit dialog: name, is_active toggle.
 * - Delete confirmation dialog (self-deletion prevented).
 */

import { useState } from "react";
import { Plus, Pencil, Trash2, Loader2, UserCog, ShieldCheck, ShieldAlert } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAdminSuperadmins,
  useCreateSuperadmin,
  useUpdateSuperadmin,
  useDeleteSuperadmin,
  type SuperadminResponse,
} from "@/lib/hooks/use-admin";
import { useAdminAuthStore } from "@/lib/hooks/use-admin-auth";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ─── Create Dialog ────────────────────────────────────────────────────────────

interface CreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function CreateSuperadminDialog({ open, onOpenChange }: CreateDialogProps) {
  const { mutate: createSuperadmin, isPending } = useCreateSuperadmin();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleClose() {
    onOpenChange(false);
    setName("");
    setEmail("");
    setPassword("");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    createSuperadmin(
      { name: name.trim(), email: email.trim(), password },
      {
        onSuccess: (data) => {
          toast.success(`Superadmin "${data.name}" creado correctamente.`);
          handleClose();
        },
        onError: (err) => {
          toast.error(
            err instanceof Error
              ? err.message
              : "No se pudo crear el superadmin. Intentalo de nuevo.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Nuevo Superadmin</DialogTitle>
          <DialogDescription>
            Crea una nueva cuenta de superadmin para la plataforma.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="create-name">Nombre</Label>
            <Input
              id="create-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Maria Lopez"
              required
              minLength={2}
              maxLength={200}
              disabled={isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-email">Correo electronico</Label>
            <Input
              id="create-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@dentalos.io"
              required
              disabled={isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-password">Contrasena</Label>
            <Input
              id="create-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimo 8 caracteres"
              required
              minLength={8}
              disabled={isPending}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creando...
                </>
              ) : (
                "Crear superadmin"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Dialog ──────────────────────────────────────────────────────────────

interface EditDialogProps {
  superadmin: SuperadminResponse | null;
  onOpenChange: (open: boolean) => void;
}

function EditSuperadminDialog({ superadmin, onOpenChange }: EditDialogProps) {
  const { mutate: updateSuperadmin, isPending } = useUpdateSuperadmin();

  const [name, setName] = useState(superadmin?.name ?? "");
  const [isActive, setIsActive] = useState(superadmin?.is_active ?? true);

  // Sync local state when the target superadmin changes
  const open = superadmin !== null;

  // Reset when dialog opens with a new superadmin
  function handleOpenChange(val: boolean) {
    if (!val) onOpenChange(false);
  }

  // Keep form in sync if superadmin prop changes while open
  const prevId = superadmin?.id;
  if (superadmin && superadmin.id !== prevId) {
    setName(superadmin.name);
    setIsActive(superadmin.is_active);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!superadmin) return;

    updateSuperadmin(
      { id: superadmin.id, payload: { name: name.trim(), is_active: isActive } },
      {
        onSuccess: () => {
          toast.success("Superadmin actualizado correctamente.");
          onOpenChange(false);
        },
        onError: (err) => {
          toast.error(
            err instanceof Error
              ? err.message
              : "No se pudo actualizar el superadmin.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Editar Superadmin</DialogTitle>
          <DialogDescription>
            Actualiza el nombre o el estado de la cuenta.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-name">Nombre</Label>
            <Input
              id="edit-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nombre del superadmin"
              required
              minLength={2}
              maxLength={200}
              disabled={isPending}
            />
          </div>

          <div className="flex items-center justify-between rounded-lg border border-[hsl(var(--border))] p-3">
            <div className="space-y-0.5">
              <p className="text-sm font-medium text-foreground">Estado de la cuenta</p>
              <p className="text-xs text-muted-foreground">
                Las cuentas inactivas no pueden iniciar sesion.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={isActive}
              onClick={() => setIsActive((prev) => !prev)}
              disabled={isPending}
              className={cn(
                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent",
                "transition-colors duration-200 ease-in-out",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2",
                isActive ? "bg-indigo-600" : "bg-[hsl(var(--muted))]",
              )}
            >
              <span
                className={cn(
                  "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow",
                  "transform transition duration-200 ease-in-out",
                  isActive ? "translate-x-5" : "translate-x-0",
                )}
              />
            </button>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                "Guardar cambios"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Delete Confirmation Dialog ───────────────────────────────────────────────

interface DeleteDialogProps {
  superadmin: SuperadminResponse | null;
  onOpenChange: (open: boolean) => void;
}

function DeleteSuperadminDialog({ superadmin, onOpenChange }: DeleteDialogProps) {
  const { mutate: deleteSuperadmin, isPending } = useDeleteSuperadmin();
  const open = superadmin !== null;

  function handleConfirm() {
    if (!superadmin) return;

    deleteSuperadmin(superadmin.id, {
      onSuccess: () => {
        toast.success(`Superadmin "${superadmin.name}" eliminado correctamente.`);
        onOpenChange(false);
      },
      onError: (err) => {
        toast.error(
          err instanceof Error
            ? err.message
            : "No se pudo eliminar el superadmin.",
        );
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={(val) => { if (!val) onOpenChange(false); }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Estas seguro?</DialogTitle>
          <DialogDescription>
            Vas a eliminar la cuenta de{" "}
            <span className="font-semibold text-foreground">{superadmin?.name}</span>.
            Esta accion no se puede deshacer.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Eliminando...
              </>
            ) : (
              "Eliminar"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Table ────────────────────────────────────────────────────────────────────

interface SuperadminsTableProps {
  superadmins: SuperadminResponse[];
  isLoading: boolean;
  currentAdminId: string | undefined;
  onEdit: (superadmin: SuperadminResponse) => void;
  onDelete: (superadmin: SuperadminResponse) => void;
}

function SuperadminsTable({
  superadmins,
  isLoading,
  currentAdminId,
  onEdit,
  onDelete,
}: SuperadminsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" aria-label="Lista de superadmins">
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Nombre
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Email
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              TOTP
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Estado
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Ultimo acceso
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Creado
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {isLoading
            ? Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-36" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-48" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-20 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-28" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-24" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <Skeleton className="h-8 w-8 rounded-md" />
                      <Skeleton className="h-8 w-8 rounded-md" />
                    </div>
                  </td>
                </tr>
              ))
            : superadmins.map((sa) => {
                const isSelf = sa.id === currentAdminId;
                return (
                  <tr
                    key={sa.id}
                    className="hover:bg-[hsl(var(--muted))] transition-colors"
                  >
                    {/* Nombre */}
                    <td className="px-4 py-3 font-medium text-foreground">
                      <div className="flex items-center gap-2">
                        <UserCog className="h-4 w-4 text-muted-foreground shrink-0" />
                        {sa.name}
                        {isSelf && (
                          <span className="text-xs text-muted-foreground">(tu)</span>
                        )}
                      </div>
                    </td>

                    {/* Email */}
                    <td className="px-4 py-3 text-muted-foreground">
                      {sa.email}
                    </td>

                    {/* TOTP */}
                    <td className="px-4 py-3">
                      {sa.totp_enabled ? (
                        <Badge variant="success" className="flex w-fit items-center gap-1">
                          <ShieldCheck className="h-3 w-3" />
                          Activo
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="flex w-fit items-center gap-1">
                          <ShieldAlert className="h-3 w-3" />
                          No configurado
                        </Badge>
                      )}
                    </td>

                    {/* Estado */}
                    <td className="px-4 py-3">
                      {sa.is_active ? (
                        <Badge variant="success">Activo</Badge>
                      ) : (
                        <Badge variant="outline">Inactivo</Badge>
                      )}
                    </td>

                    {/* Ultimo acceso */}
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {sa.last_login_at ? formatDate(sa.last_login_at) : "Nunca"}
                    </td>

                    {/* Creado */}
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {formatDate(sa.created_at)}
                    </td>

                    {/* Acciones */}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onEdit(sa)}
                          aria-label={`Editar superadmin ${sa.name}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onDelete(sa)}
                          disabled={isSelf}
                          aria-label={
                            isSelf
                              ? "No puedes eliminar tu propia cuenta"
                              : `Eliminar superadmin ${sa.name}`
                          }
                          className={cn(
                            isSelf
                              ? "opacity-40 cursor-not-allowed"
                              : "text-destructive hover:text-destructive hover:bg-destructive/10",
                          )}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
        </tbody>
      </table>

      {!isLoading && superadmins.length === 0 && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          No hay superadmins registrados todavia.
        </p>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminSuperadminsPage() {
  const admin = useAdminAuthStore((s) => s.admin);

  const { data: superadmins = [], isLoading, isError, refetch } = useAdminSuperadmins();

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<SuperadminResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<SuperadminResponse | null>(null);

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Superadmins</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Gestiona las cuentas de superadmin de la plataforma.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="sm">
          <Plus className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
          Nuevo Superadmin
        </Button>
      </div>

      {/* ── Dialogs ── */}
      <CreateSuperadminDialog open={createOpen} onOpenChange={setCreateOpen} />
      <EditSuperadminDialog
        superadmin={editTarget}
        onOpenChange={(open) => { if (!open) setEditTarget(null); }}
      />
      <DeleteSuperadminDialog
        superadmin={deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
      />

      {/* ── Error state ── */}
      {isError && (
        <Card className="border-destructive/30">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">
              No se pudo cargar la lista de superadmins.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => refetch()}
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Table card ── */}
      {!isError && (
        <Card className="overflow-hidden">
          <CardHeader className="pb-0">
            <CardTitle className="text-base">
              {isLoading
                ? "Cargando..."
                : `${superadmins.length} superadmin${superadmins.length !== 1 ? "s" : ""} en total`}
            </CardTitle>
          </CardHeader>
          <SuperadminsTable
            superadmins={superadmins}
            isLoading={isLoading}
            currentAdminId={admin?.id}
            onEdit={setEditTarget}
            onDelete={setDeleteTarget}
          />
        </Card>
      )}
    </div>
  );
}
