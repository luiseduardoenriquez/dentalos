"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { UserPlus, Lock, MoreVertical, UserX, Edit2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { useUsers, useUpdateUser, useDeactivateUser } from "@/lib/hooks/use-users";
import { useAuth } from "@/lib/hooks/use-auth";
import { useToast } from "@/lib/hooks/use-toast";
import { apiPost } from "@/lib/api-client";
import { getInitials } from "@/lib/utils";
import type { TeamUser } from "@/lib/hooks/use-users";

// ─── Constants ────────────────────────────────────────────────────────────────

const ASSIGNABLE_ROLES = [
  { value: "doctor", label: "Doctor" },
  { value: "assistant", label: "Asistente" },
  { value: "receptionist", label: "Recepcionista" },
];

const ROLE_LABELS: Record<string, string> = {
  clinic_owner: "Propietario",
  doctor: "Doctor",
  assistant: "Asistente",
  receptionist: "Recepcionista",
  patient: "Paciente",
  superadmin: "Superadmin",
};

const ROLE_BADGE_VARIANT: Record<
  string,
  "default" | "secondary" | "success" | "warning" | "outline"
> = {
  clinic_owner: "default",
  doctor: "success",
  assistant: "warning",
  receptionist: "secondary",
};

// ─── Invite Schema ────────────────────────────────────────────────────────────

const inviteSchema = z.object({
  email: z.string().email("Ingresa un correo electrónico válido").transform((v) => v.toLowerCase()),
  role: z.enum(["doctor", "assistant", "receptionist"], {
    errorMap: () => ({ message: "Selecciona un rol válido" }),
  }),
});

type InviteFormValues = z.infer<typeof inviteSchema>;

// ─── Form Field Error ─────────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-destructive-600 dark:text-destructive-400">{message}</p>;
}

// ─── Member Row ───────────────────────────────────────────────────────────────

interface MemberRowProps {
  member: TeamUser;
  currentUserId: string;
  isOwner: boolean;
  onEditRole: (member: TeamUser) => void;
  onDeactivate: (member: TeamUser) => void;
}

function MemberRow({ member, currentUserId, isOwner, onEditRole, onDeactivate }: MemberRowProps) {
  const isSelf = member.id === currentUserId;
  const canManage = isOwner && !isSelf && member.role !== "clinic_owner";

  return (
    <div className="flex items-center justify-between gap-3 py-3 px-4">
      <div className="flex items-center gap-3 min-w-0">
        <Avatar className="h-9 w-9 shrink-0">
          <AvatarFallback className="text-sm font-semibold">{getInitials(member.name)}</AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-foreground truncate">{member.name}</p>
            {isSelf && (
              <span className="text-xs text-[hsl(var(--muted-foreground))]">(tú)</span>
            )}
          </div>
          <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{member.email}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <Badge variant={ROLE_BADGE_VARIANT[member.role] ?? "outline"}>
          {ROLE_LABELS[member.role] ?? member.role}
        </Badge>

        {member.is_active ? (
          <Badge variant="success" className="hidden sm:flex">
            Activo
          </Badge>
        ) : (
          <Badge variant="secondary" className="hidden sm:flex">
            Inactivo
          </Badge>
        )}

        {canManage && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                aria-label="Opciones del miembro"
                className="flex h-8 w-8 items-center justify-center rounded-md text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] hover:text-foreground transition-colors"
              >
                <MoreVertical className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEditRole(member)}>
                <Edit2 className="mr-2 h-4 w-4" />
                Cambiar rol
              </DropdownMenuItem>
              {member.is_active && (
                <DropdownMenuItem
                  onClick={() => onDeactivate(member)}
                  className="text-destructive-600 focus:text-destructive-600"
                >
                  <UserX className="mr-2 h-4 w-4" />
                  Desactivar
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  );
}

// ─── Team List Skeleton ────────────────────────────────────────────────────────

function TeamSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-3 py-3 px-4">
          <Skeleton className="h-9 w-9 rounded-full" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-48" />
          </div>
          <Skeleton className="h-5 w-16" />
        </div>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TeamPage() {
  const { user, has_role } = useAuth();
  const { success, error } = useToast();
  const isOwner = has_role("clinic_owner");

  const [showInviteDialog, setShowInviteDialog] = React.useState(false);
  const [isInviting, setIsInviting] = React.useState(false);

  const [editingMember, setEditingMember] = React.useState<TeamUser | null>(null);
  const [editRole, setEditRole] = React.useState("");
  const [showEditDialog, setShowEditDialog] = React.useState(false);

  const [deactivatingMember, setDeactivatingMember] = React.useState<TeamUser | null>(null);
  const [showDeactivateDialog, setShowDeactivateDialog] = React.useState(false);

  const { data, isLoading } = useUsers({ page: 1, page_size: 50 });
  const members = data?.items ?? [];

  // ─── Invite form ──────────────────────────────────────────────────────────
  const {
    register: inviteRegister,
    handleSubmit: handleInviteSubmit,
    setValue: setInviteValue,
    reset: resetInvite,
    formState: { errors: inviteErrors },
  } = useForm<InviteFormValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: "", role: "doctor" },
  });

  async function onInviteSubmit(values: InviteFormValues) {
    setIsInviting(true);
    try {
      await apiPost("/auth/invite", values);
      success(
        "Invitación enviada",
        `Se envió una invitación a ${values.email} con el rol de ${ROLE_LABELS[values.role]}.`,
      );
      resetInvite();
      setShowInviteDialog(false);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "No se pudo enviar la invitación. Inténtalo de nuevo.";
      error("Error al invitar", message);
    } finally {
      setIsInviting(false);
    }
  }

  // ─── Edit role ────────────────────────────────────────────────────────────
  // Hooks must be called unconditionally — use empty string as sentinel when no
  // member is selected; the mutations simply won't fire in that state.
  const updateUser = useUpdateUser(editingMember?.id ?? "");

  function handleOpenEditRole(member: TeamUser) {
    setEditingMember(member);
    setEditRole(member.role);
    setShowEditDialog(true);
  }

  function handleSaveRole() {
    if (!editingMember) return;
    updateUser.mutate(
      { role: editRole },
      {
        onSuccess: () => {
          setShowEditDialog(false);
          setEditingMember(null);
        },
      },
    );
  }

  // ─── Deactivate ───────────────────────────────────────────────────────────
  const deactivateUser = useDeactivateUser(deactivatingMember?.id ?? "");

  function handleOpenDeactivate(member: TeamUser) {
    setDeactivatingMember(member);
    setShowDeactivateDialog(true);
  }

  function handleConfirmDeactivate() {
    if (!deactivatingMember) return;
    deactivateUser.mutate(undefined, {
      onSuccess: () => {
        setShowDeactivateDialog(false);
        setDeactivatingMember(null);
      },
    });
  }

  return (
    <>
      <div className="max-w-3xl space-y-6">
        {/* ─── Page Header ──────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Equipo</h1>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
              Gestiona los miembros del equipo de la clínica.
            </p>
          </div>
          {isOwner && (
            <Button onClick={() => setShowInviteDialog(true)}>
              <UserPlus className="mr-2 h-4 w-4" />
              Invitar miembro
            </Button>
          )}
        </div>

        {/* Read-only notice for non-owners */}
        {!isOwner && (
          <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
            <Lock className="h-4 w-4 shrink-0" />
            Solo el propietario de la clínica puede gestionar el equipo.
          </div>
        )}

        {/* ─── Team List ────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Miembros del equipo
              {data && (
                <span className="ml-2 text-sm font-normal text-[hsl(var(--muted-foreground))]">
                  ({data.total})
                </span>
              )}
            </CardTitle>
            <CardDescription>
              Todos los usuarios con acceso a la clínica.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <TeamSkeleton />
            ) : members.length === 0 ? (
              <p className="py-8 text-center text-sm text-[hsl(var(--muted-foreground))]">
                No hay miembros en el equipo.
              </p>
            ) : (
              <div className="divide-y divide-[hsl(var(--border))]">
                {members.map((member) => (
                  <MemberRow
                    key={member.id}
                    member={member}
                    currentUserId={user?.id ?? ""}
                    isOwner={isOwner}
                    onEditRole={handleOpenEditRole}
                    onDeactivate={handleOpenDeactivate}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ─── Invite Dialog ────────────────────────────────────────────────── */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invitar miembro del equipo</DialogTitle>
            <DialogDescription>
              El usuario recibirá un correo con instrucciones para activar su cuenta.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleInviteSubmit(onInviteSubmit)} noValidate className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="invite-email">
                Correo electrónico <span className="text-destructive-600">*</span>
              </Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="medico@clinica.com"
                {...inviteRegister("email")}
                aria-invalid={!!inviteErrors.email}
              />
              <FieldError message={inviteErrors.email?.message} />
            </div>

            <div className="space-y-1">
              <Label htmlFor="invite-role">
                Rol <span className="text-destructive-600">*</span>
              </Label>
              <Select
                defaultValue="doctor"
                onValueChange={(val) =>
                  setInviteValue("role", val as InviteFormValues["role"], {
                    shouldValidate: true,
                  })
                }
              >
                <SelectTrigger id="invite-role" aria-label="Rol del usuario">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASSIGNABLE_ROLES.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FieldError message={inviteErrors.role?.message} />
            </div>

            <DialogFooter className="flex-col-reverse sm:flex-row gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowInviteDialog(false);
                  resetInvite();
                }}
                disabled={isInviting}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={isInviting}>
                {isInviting ? "Enviando..." : "Enviar invitación"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ─── Edit Role Dialog ─────────────────────────────────────────────── */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cambiar rol</DialogTitle>
            <DialogDescription>
              Actualiza el rol de{" "}
              <span className="font-semibold text-foreground">
                {editingMember?.name}
              </span>{" "}
              en la clínica.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-1">
            <Label htmlFor="edit-role">Nuevo rol</Label>
            <Select
              value={editRole}
              onValueChange={setEditRole}
            >
              <SelectTrigger id="edit-role" aria-label="Nuevo rol">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ASSIGNABLE_ROLES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter className="flex-col-reverse sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setShowEditDialog(false)}
              disabled={updateUser.isPending}
            >
              Cancelar
            </Button>
            <Button onClick={handleSaveRole} disabled={updateUser.isPending}>
              {updateUser.isPending ? "Guardando..." : "Guardar rol"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Deactivate Dialog ────────────────────────────────────────────── */}
      <Dialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Desactivar miembro</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que deseas desactivar a{" "}
              <span className="font-semibold text-foreground">
                {deactivatingMember?.name}
              </span>
              ? Perderá acceso a la clínica de inmediato.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col-reverse sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setShowDeactivateDialog(false)}
              disabled={deactivateUser.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDeactivate}
              disabled={deactivateUser.isPending}
            >
              {deactivateUser.isPending ? "Desactivando..." : "Desactivar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
