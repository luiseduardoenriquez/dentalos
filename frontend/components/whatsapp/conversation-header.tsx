"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Archive, UserPlus, ExternalLink, MoreVertical, ArchiveRestore } from "lucide-react";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { WhatsAppConversation } from "@/components/whatsapp/conversation-list";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AssignPayload {
  assigned_user_id: string | null;
}

interface ConversationHeaderProps {
  conversation: WhatsAppConversation;
}

// ─── ConversationHeader ───────────────────────────────────────────────────────

export function ConversationHeader({ conversation }: ConversationHeaderProps) {
  const queryClient = useQueryClient();
  const { success, error } = useToast();
  const [assignDialogOpen, setAssignDialogOpen] = React.useState(false);

  const displayName = conversation.patient_name ?? "Desconocido";
  const initials = displayName
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  // Archive / unarchive
  const { mutate: toggleArchive, isPending: isArchiving } = useMutation({
    mutationFn: () =>
      apiPut<WhatsAppConversation>(
        `/messaging/conversations/${conversation.id}`,
        {
          status: conversation.status === "active" ? "archived" : "active",
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-conversations"] });
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-conversation", conversation.id],
      });
      success(
        conversation.status === "active"
          ? "Conversación archivada"
          : "Conversación restaurada",
      );
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar la conversación.";
      error("Error", message);
    },
  });

  // Assign to user
  const { mutate: assign, isPending: isAssigning } = useMutation({
    mutationFn: (payload: AssignPayload) =>
      apiPut<WhatsAppConversation>(
        `/messaging/conversations/${conversation.id}/assign`,
        payload,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-conversations"] });
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-conversation", conversation.id],
      });
      setAssignDialogOpen(false);
      success("Asignación actualizada");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "No se pudo asignar la conversación.";
      error("Error al asignar", message);
    },
  });

  return (
    <>
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Contact avatar */}
        <Avatar className="h-9 w-9 shrink-0">
          <AvatarFallback className="text-sm bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
            {initials}
          </AvatarFallback>
        </Avatar>

        {/* Name + phone */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold truncate">{displayName}</p>
            {conversation.patient_id && (
              <Link
                href={`/patients/${conversation.patient_id}`}
                className="shrink-0 text-[hsl(var(--muted-foreground))] hover:text-primary-600 transition-colors"
                title="Ver perfil del paciente"
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
          <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">
            {conversation.phone_number}
            {conversation.assigned_user_name && (
              <span className="ml-2 text-primary-600 dark:text-primary-400">
                · Asignado a {conversation.assigned_user_name}
              </span>
            )}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {/* Assign button */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setAssignDialogOpen(true)}
            disabled={isAssigning}
            title="Asignar conversación"
          >
            <UserPlus className="h-4 w-4" />
          </Button>

          {/* More actions */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {conversation.patient_id && (
                <>
                  <DropdownMenuItem asChild>
                    <Link href={`/patients/${conversation.patient_id}`}>
                      <ExternalLink className="h-3.5 w-3.5 mr-2" />
                      Ver ficha del paciente
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem
                onClick={() => toggleArchive()}
                disabled={isArchiving}
                className={cn(
                  conversation.status === "active"
                    ? "text-orange-600 dark:text-orange-400"
                    : "text-green-600 dark:text-green-400",
                )}
              >
                {conversation.status === "active" ? (
                  <>
                    <Archive className="h-3.5 w-3.5 mr-2" />
                    Archivar conversación
                  </>
                ) : (
                  <>
                    <ArchiveRestore className="h-3.5 w-3.5 mr-2" />
                    Restaurar conversación
                  </>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Assign dialog */}
      <AssignDialog
        open={assignDialogOpen}
        currentAssignee={conversation.assigned_user_id}
        onClose={() => setAssignDialogOpen(false)}
        onAssign={(userId) => assign({ assigned_user_id: userId })}
        isLoading={isAssigning}
      />
    </>
  );
}

// ─── AssignDialog ─────────────────────────────────────────────────────────────

interface StaffMember {
  id: string;
  name: string;
  role: string;
}

interface AssignDialogProps {
  open: boolean;
  currentAssignee: string | null;
  onClose: () => void;
  onAssign: (userId: string | null) => void;
  isLoading: boolean;
}

function AssignDialog({
  open,
  currentAssignee,
  onClose,
  onAssign,
  isLoading,
}: AssignDialogProps) {
  const { data: staffData, isLoading: isLoadingStaff } = useStaffList(open);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Asignar conversación</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
          {/* Unassign option */}
          <button
            type="button"
            onClick={() => onAssign(null)}
            disabled={isLoading || currentAssignee === null}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-left",
              "hover:bg-[hsl(var(--muted))] transition-colors",
              currentAssignee === null && "opacity-50 cursor-not-allowed",
            )}
          >
            <Avatar className="h-7 w-7">
              <AvatarFallback className="text-xs">—</AvatarFallback>
            </Avatar>
            <span className="text-[hsl(var(--muted-foreground))]">
              Sin asignación
            </span>
          </button>

          {isLoadingStaff && (
            <p className="text-sm text-[hsl(var(--muted-foreground))] px-3 py-2">
              Cargando personal...
            </p>
          )}

          {staffData?.map((staff) => (
            <button
              key={staff.id}
              type="button"
              onClick={() => onAssign(staff.id)}
              disabled={isLoading || staff.id === currentAssignee}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-left",
                "hover:bg-[hsl(var(--muted))] transition-colors",
                staff.id === currentAssignee
                  ? "bg-primary-50 dark:bg-primary-900/20"
                  : "",
              )}
            >
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-xs bg-slate-200 dark:bg-zinc-700">
                  {staff.name
                    .split(" ")
                    .slice(0, 2)
                    .map((n) => n[0])
                    .join("")
                    .toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{staff.name}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  {ROLE_LABELS[staff.role] ?? staff.role}
                </p>
              </div>
              {staff.id === currentAssignee && (
                <span className="text-xs text-primary-600 dark:text-primary-400 font-medium shrink-0">
                  Actual
                </span>
              )}
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  clinic_owner: "Propietario",
  doctor: "Doctor",
  assistant: "Asistente",
  receptionist: "Recepcionista",
};

interface StaffListResponse {
  items: StaffMember[];
}

function useStaffList(enabled: boolean) {
  const { data, isLoading } = useQuery({
    queryKey: ["staff-list-assign"],
    queryFn: () =>
      apiGet<StaffListResponse>("/users?page_size=100&is_active=true"),
    enabled,
    staleTime: 5 * 60_000,
  });

  return { data: data?.items, isLoading };
}

