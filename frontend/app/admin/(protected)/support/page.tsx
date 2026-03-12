"use client";

/**
 * Admin support chat inbox page.
 *
 * Two-panel layout:
 * - Left panel: list of support threads, sorted by last_message_at desc.
 *   Shows tenant name, truncated last message, relative timestamp, unread
 *   badge, and open/closed status badge. Auto-refreshes every 60s.
 * - Right panel: selected thread's full message history. Admin messages on
 *   the right (indigo), clinic_owner messages on the left (gray). Text input
 *   at bottom to send new messages. Auto-refreshes every 15s.
 *
 * Mobile: stacks vertically (thread list on top, messages below).
 */

import { useState, useRef, useEffect } from "react";
import { Send, MessageSquare, Circle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  useSupportThreads,
  useSupportThread,
  useSendSupportMessage,
  type SupportThreadItem,
  type SupportMessageItem,
} from "@/lib/hooks/use-admin";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Returns a relative time string in es-419 using Intl.RelativeTimeFormat.
 * Falls back to a short date if the timestamp is older than 7 days.
 */
function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const now = Date.now();
  const diffMs = date.getTime() - now;
  const diffSecs = Math.round(diffMs / 1000);
  const diffMins = Math.round(diffSecs / 60);
  const diffHours = Math.round(diffMins / 60);
  const diffDays = Math.round(diffHours / 24);

  const rtf = new Intl.RelativeTimeFormat("es-419", { numeric: "auto" });

  if (Math.abs(diffSecs) < 60) return rtf.format(diffSecs, "second");
  if (Math.abs(diffMins) < 60) return rtf.format(diffMins, "minute");
  if (Math.abs(diffHours) < 24) return rtf.format(diffHours, "hour");
  if (Math.abs(diffDays) <= 7) return rtf.format(diffDays, "day");

  return date.toLocaleDateString("es-419", {
    day: "numeric",
    month: "short",
  });
}

/**
 * Truncates a string to maxLen characters, appending "..." if cut.
 */
function truncate(text: string | null, maxLen = 60): string {
  if (!text) return "Sin mensajes";
  if (text.length <= maxLen) return text;
  return `${text.slice(0, maxLen)}...`;
}

/**
 * Format a full timestamp for message bubbles: HH:mm · DD MMM
 */
function formatMessageTime(iso: string): string {
  const d = new Date(iso);
  const time = d.toLocaleTimeString("es-419", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const date = d.toLocaleDateString("es-419", {
    day: "numeric",
    month: "short",
  });
  return `${time} · ${date}`;
}

// ─── Thread List Skeleton ──────────────────────────────────────────────────────

function ThreadListSkeleton() {
  return (
    <div className="space-y-1 p-2" aria-label="Cargando conversaciones...">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="flex flex-col gap-1.5 rounded-lg p-3 border border-[hsl(var(--border))]"
        >
          <div className="flex items-center justify-between gap-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3.5 w-14" />
          </div>
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-2/3" />
        </div>
      ))}
    </div>
  );
}

// ─── Thread List Item ──────────────────────────────────────────────────────────

interface ThreadListItemProps {
  thread: SupportThreadItem;
  isSelected: boolean;
  onSelect: (tenantId: string) => void;
}

function ThreadListItem({ thread, isSelected, onSelect }: ThreadListItemProps) {
  const isOpen = thread.status === "open";
  const hasUnread = thread.unread_count > 0;

  return (
    <button
      type="button"
      onClick={() => onSelect(thread.tenant_id)}
      className={cn(
        "w-full text-left rounded-lg px-3 py-3 transition-colors",
        "border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
        isSelected
          ? "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/40 dark:border-indigo-800"
          : "border-transparent hover:bg-[hsl(var(--muted))] hover:border-[hsl(var(--border))]",
      )}
      aria-label={`Conversacion con ${thread.tenant_name}`}
      aria-pressed={isSelected}
    >
      {/* Row 1: name + timestamp */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <span
          className={cn(
            "text-sm font-semibold leading-tight truncate",
            isSelected
              ? "text-indigo-700 dark:text-indigo-300"
              : "text-foreground",
          )}
        >
          {thread.tenant_name}
        </span>
        <span className="shrink-0 text-[11px] text-muted-foreground whitespace-nowrap">
          {relativeTime(thread.last_message_at)}
        </span>
      </div>

      {/* Row 2: last message preview */}
      <p
        className={cn(
          "text-xs leading-snug mb-2",
          hasUnread ? "text-foreground font-medium" : "text-muted-foreground",
        )}
      >
        {truncate(thread.last_message)}
      </p>

      {/* Row 3: status badge + unread count */}
      <div className="flex items-center justify-between gap-2">
        {/* Status badge */}
        <span
          className={cn(
            "inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full border",
            isOpen
              ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800"
              : "bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
          )}
        >
          <Circle
            className={cn(
              "h-1.5 w-1.5",
              isOpen ? "fill-emerald-500" : "fill-slate-400",
            )}
            aria-hidden="true"
          />
          {isOpen ? "Abierto" : "Cerrado"}
        </span>

        {/* Unread badge */}
        {hasUnread && (
          <span
            className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold"
            aria-label={`${thread.unread_count} mensajes sin leer`}
          >
            {thread.unread_count > 99 ? "99+" : thread.unread_count}
          </span>
        )}
      </div>
    </button>
  );
}

// ─── Message Bubble ────────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: SupportMessageItem;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isAdmin = message.sender_type === "admin";

  return (
    <div
      className={cn(
        "flex flex-col max-w-[75%] gap-1",
        isAdmin ? "self-end items-end" : "self-start items-start",
      )}
    >
      {/* Sender name */}
      <span className="text-[11px] font-medium text-muted-foreground px-1">
        {message.sender_name}
      </span>

      {/* Bubble */}
      <div
        className={cn(
          "rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isAdmin
            ? "bg-indigo-600 text-white rounded-tr-sm"
            : "bg-[hsl(var(--muted))] text-foreground border border-[hsl(var(--border))] rounded-tl-sm",
        )}
      >
        {message.content}
      </div>

      {/* Timestamp */}
      <span className="text-[10px] text-muted-foreground px-1">
        {formatMessageTime(message.created_at)}
      </span>
    </div>
  );
}

// ─── Chat Messages Skeleton ────────────────────────────────────────────────────

function ChatMessagesSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4" aria-label="Cargando mensajes...">
      {/* Simulate alternating left/right bubbles */}
      {[false, true, false, false, true, false].map((isRight, i) => (
        <div
          key={i}
          className={cn(
            "flex flex-col gap-1",
            isRight ? "items-end" : "items-start",
          )}
        >
          <Skeleton className="h-3 w-20" />
          <Skeleton
            className={cn("h-10 rounded-2xl", isRight ? "w-52" : "w-64")}
          />
        </div>
      ))}
    </div>
  );
}

// ─── Empty Chat Placeholder ────────────────────────────────────────────────────

function EmptyChatPlaceholder() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center px-8">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[hsl(var(--muted))]">
        <MessageSquare
          className="h-7 w-7 text-muted-foreground"
          aria-hidden="true"
        />
      </div>
      <p className="text-sm font-medium text-muted-foreground">
        Selecciona una conversacion
      </p>
      <p className="text-xs text-muted-foreground max-w-xs">
        Elige una clinica de la lista para ver y responder sus mensajes de
        soporte.
      </p>
    </div>
  );
}

// ─── Chat Area ────────────────────────────────────────────────────────────────

interface ChatAreaProps {
  selectedTenantId: string | null;
}

function ChatArea({ selectedTenantId }: ChatAreaProps) {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useSupportThread(selectedTenantId ?? "");
  const { mutate: sendMessage, isPending: isSending } =
    useSendSupportMessage();

  // Scroll to bottom whenever messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [data?.messages]);

  function handleSend() {
    const content = inputValue.trim();
    if (!content || !selectedTenantId || isSending) return;

    sendMessage(
      { tenantId: selectedTenantId, content },
      {
        onSuccess: () => {
          setInputValue("");
        },
        onError: () => {
          toast.error("No se pudo enviar el mensaje. Intenta de nuevo.");
        },
      },
    );
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (!selectedTenantId) {
    return <EmptyChatPlaceholder />;
  }

  return (
    <div className="flex flex-1 flex-col min-h-0">
      {/* Thread header */}
      {data?.thread && (
        <div className="shrink-0 px-4 py-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--card))]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-foreground">
                {data.thread.tenant_name}
              </h2>
              <p className="text-xs text-muted-foreground">
                {data.messages.length}{" "}
                {data.messages.length === 1 ? "mensaje" : "mensajes"}
              </p>
            </div>
            {/* Status badge in header */}
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded-full border",
                data.thread.status === "open"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800"
                  : "bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
              )}
            >
              <Circle
                className={cn(
                  "h-1.5 w-1.5",
                  data.thread.status === "open"
                    ? "fill-emerald-500"
                    : "fill-slate-400",
                )}
                aria-hidden="true"
              />
              {data.thread.status === "open" ? "Abierto" : "Cerrado"}
            </span>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {isLoading ? (
          <ChatMessagesSkeleton />
        ) : data?.messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-muted-foreground">
              Sin mensajes en esta conversacion.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3 p-4">
            {data?.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-[hsl(var(--border))] bg-[hsl(var(--card))] p-3">
        <div className="flex items-end gap-2">
          <textarea
            className={cn(
              "flex-1 resize-none rounded-lg border border-[hsl(var(--border))]",
              "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
              "placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
              "min-h-[40px] max-h-[120px]",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            )}
            rows={1}
            placeholder="Escribe un mensaje... (Enter para enviar)"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending}
            aria-label="Mensaje de soporte"
          />
          <Button
            type="button"
            size="icon"
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending}
            className="shrink-0 bg-indigo-600 hover:bg-indigo-700 text-white h-10 w-10"
            aria-label="Enviar mensaje"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        <p className="mt-1.5 text-[10px] text-muted-foreground">
          Shift+Enter para nueva linea
        </p>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Admin support inbox page.
 *
 * Manages the selected thread tenant ID in local state.
 * Thread list auto-refreshes every 60s (configured in useSupportThreads).
 * Active thread auto-refreshes every 15s (configured in useSupportThread).
 */
export default function AdminSupportPage() {
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);

  const {
    data: threadsData,
    isLoading: isLoadingThreads,
    isError: isErrorThreads,
    refetch: refetchThreads,
  } = useSupportThreads();

  const threads = threadsData?.items ?? [];
  const totalUnread = threadsData?.unread_total ?? 0;

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-7rem)]">
      {/* ── Page header ── */}
      <div className="shrink-0 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Soporte</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Chat de soporte con propietarios de clinicas
          </p>
        </div>
        {totalUnread > 0 && (
          <div className="flex items-center gap-2 rounded-full bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 px-3 py-1.5">
            <span
              className="flex h-2 w-2 rounded-full bg-red-500 animate-pulse"
              aria-hidden="true"
            />
            <span className="text-xs font-semibold text-red-700 dark:text-red-400">
              {totalUnread} sin leer
            </span>
          </div>
        )}
      </div>

      {/* ── Two-panel layout ── */}
      <div className="flex flex-col md:flex-row flex-1 min-h-0 gap-4">
        {/* ── Left panel: thread list ── */}
        <aside
          className={cn(
            "md:w-80 lg:w-96 shrink-0",
            "flex flex-col",
            "rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]",
            "overflow-hidden",
            // On mobile: fixed height for thread list, chat below
            "h-64 md:h-auto",
          )}
          aria-label="Lista de conversaciones"
        >
          {/* Panel header */}
          <div className="shrink-0 px-4 py-3 border-b border-[hsl(var(--border))]">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-foreground">
                Conversaciones
              </span>
              {threadsData && (
                <span className="text-xs text-muted-foreground tabular-nums">
                  {threadsData.total}{" "}
                  {threadsData.total === 1 ? "total" : "en total"}
                </span>
              )}
            </div>
          </div>

          {/* Thread list body */}
          <div className="flex-1 overflow-y-auto min-h-0">
            {isLoadingThreads ? (
              <ThreadListSkeleton />
            ) : isErrorThreads ? (
              <div className="flex flex-col items-center justify-center gap-3 p-6 text-center h-full">
                <p className="text-sm text-muted-foreground">
                  No se pudieron cargar las conversaciones.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetchThreads()}
                >
                  Reintentar
                </Button>
              </div>
            ) : threads.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 p-6 text-center h-full">
                <MessageSquare
                  className="h-8 w-8 text-muted-foreground opacity-50"
                  aria-hidden="true"
                />
                <p className="text-sm text-muted-foreground">
                  No hay conversaciones activas.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-0.5 p-2">
                {threads.map((thread) => (
                  <ThreadListItem
                    key={thread.id}
                    thread={thread}
                    isSelected={selectedTenantId === thread.tenant_id}
                    onSelect={setSelectedTenantId}
                  />
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* ── Right panel: chat messages ── */}
        <section
          className={cn(
            "flex-1 min-w-0",
            "flex flex-col",
            "rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]",
            "overflow-hidden",
          )}
          aria-label="Area de chat"
        >
          <ChatArea selectedTenantId={selectedTenantId} />
        </section>
      </div>
    </div>
  );
}
