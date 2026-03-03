"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, RefreshCw, MessageSquare } from "lucide-react";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface WhatsAppConversation {
  id: string;
  phone_number: string;
  patient_id: string | null;
  patient_name: string | null;
  last_message_preview: string | null;
  last_message_at: string | null;
  unread_count: number;
  status: "active" | "archived";
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  assigned_user_avatar_url: string | null;
  created_at: string;
}

interface ConversationListResponse {
  items: WhatsAppConversation[];
  total: number;
  page: number;
  page_size: number;
}

type StatusFilter = "active" | "archived";

interface ConversationListProps {
  selectedId: string | null;
  onSelectConversation: (id: string) => void;
}

// ─── Query Key ────────────────────────────────────────────────────────────────

const conversationsKey = (status: StatusFilter, page: number) =>
  ["whatsapp-conversations", status, page] as const;

// ─── ConversationList ─────────────────────────────────────────────────────────

export function ConversationList({
  selectedId,
  onSelectConversation,
}: ConversationListProps) {
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("active");
  const [search, setSearch] = React.useState("");
  const [page] = React.useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: conversationsKey(statusFilter, page),
    queryFn: () =>
      apiGet<ConversationListResponse>(
        `/messaging/conversations?status=${statusFilter}&page=${page}&page_size=50`,
      ),
    staleTime: 30_000,
    refetchInterval: 15_000, // Poll every 15s for new conversations
  });

  // Client-side search filter
  const filtered = React.useMemo(() => {
    if (!data?.items) return [];
    if (!search.trim()) return data.items;
    const q = search.toLowerCase();
    return data.items.filter(
      (c) =>
        c.phone_number.includes(q) ||
        (c.patient_name ?? "").toLowerCase().includes(q) ||
        (c.last_message_preview ?? "").toLowerCase().includes(q),
    );
  }, [data?.items, search]);

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="px-3 pt-3 pb-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          <Input
            type="search"
            placeholder="Buscar por nombre o teléfono..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex border-b border-[hsl(var(--border))] mx-3">
        {(["active", "archived"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={cn(
              "flex-1 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              statusFilter === s
                ? "border-primary-600 text-primary-700 dark:text-primary-300"
                : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground hover:border-[hsl(var(--border))]",
            )}
          >
            {s === "active" ? "Activas" : "Archivadas"}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex flex-col gap-0">
            {Array.from({ length: 8 }).map((_, i) => (
              <ConversationSkeleton key={i} />
            ))}
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center py-12 gap-2 text-[hsl(var(--muted-foreground))]">
            <RefreshCw className="h-5 w-5" />
            <p className="text-sm">No se pudieron cargar las conversaciones</p>
          </div>
        )}

        {!isLoading && !isError && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 gap-2 text-[hsl(var(--muted-foreground))]">
            <MessageSquare className="h-6 w-6 opacity-50" />
            <p className="text-sm">
              {search ? "Sin resultados para la búsqueda" : "Sin conversaciones"}
            </p>
          </div>
        )}

        {!isLoading && !isError && filtered.map((conv) => (
          <ConversationItem
            key={conv.id}
            conversation={conv}
            isSelected={conv.id === selectedId}
            onClick={() => onSelectConversation(conv.id)}
          />
        ))}
      </div>
    </div>
  );
}

// ─── ConversationItem ─────────────────────────────────────────────────────────

interface ConversationItemProps {
  conversation: WhatsAppConversation;
  isSelected: boolean;
  onClick: () => void;
}

function ConversationItem({ conversation, isSelected, onClick }: ConversationItemProps) {
  const displayName = conversation.patient_name ?? "Desconocido";
  const initials = displayName
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  const formattedTime = conversation.last_message_at
    ? formatRelativeTime(conversation.last_message_at)
    : "";

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full flex items-start gap-3 px-3 py-3 text-left transition-colors",
        "hover:bg-[hsl(var(--muted))] focus-visible:outline-none focus-visible:bg-[hsl(var(--muted))]",
        isSelected && "bg-primary-50 dark:bg-primary-900/20 hover:bg-primary-50 dark:hover:bg-primary-900/20",
      )}
      aria-pressed={isSelected}
    >
      {/* Avatar */}
      <Avatar className="h-10 w-10 shrink-0">
        <AvatarFallback className="text-sm bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
          {initials}
        </AvatarFallback>
      </Avatar>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span
            className={cn(
              "text-sm truncate",
              conversation.unread_count > 0 ? "font-semibold" : "font-medium",
            )}
          >
            {displayName}
          </span>
          <span className="text-xs text-[hsl(var(--muted-foreground))] shrink-0">
            {formattedTime}
          </span>
        </div>

        <p className="text-xs text-[hsl(var(--muted-foreground))] truncate mt-0.5">
          {conversation.phone_number}
        </p>

        <div className="flex items-center justify-between gap-2 mt-0.5">
          <p
            className={cn(
              "text-xs truncate",
              conversation.unread_count > 0
                ? "text-foreground font-medium"
                : "text-[hsl(var(--muted-foreground))]",
            )}
          >
            {conversation.last_message_preview ?? "Sin mensajes"}
          </p>

          <div className="flex items-center gap-1.5 shrink-0">
            {/* Assigned user avatar */}
            {conversation.assigned_user_name && (
              <Avatar className="h-5 w-5">
                <AvatarFallback className="text-[10px] bg-slate-200 dark:bg-zinc-700">
                  {conversation.assigned_user_name
                    .split(" ")
                    .slice(0, 2)
                    .map((n) => n[0])
                    .join("")
                    .toUpperCase()}
                </AvatarFallback>
              </Avatar>
            )}

            {/* Unread badge */}
            {conversation.unread_count > 0 && (
              <Badge className="h-5 min-w-5 px-1 text-[10px] rounded-full bg-primary-600 text-white">
                {conversation.unread_count > 99 ? "99+" : conversation.unread_count}
              </Badge>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function ConversationSkeleton() {
  return (
    <div className="flex items-start gap-3 px-3 py-3">
      <Skeleton className="h-10 w-10 rounded-full shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="flex justify-between">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-12" />
        </div>
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-3 w-full" />
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMins < 1) return "Ahora";
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays === 1) return "Ayer";
  if (diffDays < 7) return `${diffDays}d`;

  return date.toLocaleDateString("es-CO", { day: "numeric", month: "short" });
}
