"use client";

import { useState } from "react";
import {
  usePortalMessages,
  usePortalSendMessage,
  type PortalMessageThread,
} from "@/lib/hooks/use-portal";

// ─── Thread Card ──────────────────────────────────────────────────────────────

function ThreadCard({
  thread,
  isSelected,
  onClick,
}: {
  thread: PortalMessageThread;
  isSelected: boolean;
  onClick: () => void;
}) {
  const lastMessage = thread.messages[thread.messages.length - 1];

  return (
    <button
      onClick={onClick}
      className={`w-full text-left bg-white dark:bg-zinc-900 rounded-xl border p-4 transition-colors ${
        isSelected
          ? "border-primary-400 dark:border-primary-600"
          : "border-[hsl(var(--border))] hover:border-primary-300 dark:hover:border-primary-700"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-sm text-[hsl(var(--foreground))] truncate">
            {thread.subject || "Consulta a la clínica"}
          </p>
          {lastMessage && (
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5 truncate">
              {lastMessage.sender_type === "patient" ? "Tú: " : ""}
              {lastMessage.body}
            </p>
          )}
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
            {new Date(thread.last_message_at).toLocaleDateString("es-CO", {
              day: "numeric",
              month: "short",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
        {thread.unread_count > 0 && (
          <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs rounded-full bg-primary-600 text-white shrink-0">
            {thread.unread_count}
          </span>
        )}
      </div>
    </button>
  );
}

// ─── Thread Detail ─────────────────────────────────────────────────────────────

function ThreadDetail({
  thread,
  onReply,
  isSending,
}: {
  thread: PortalMessageThread;
  onReply: (threadId: string, body: string) => void;
  isSending: boolean;
}) {
  const [replyBody, setReplyBody] = useState("");

  function handleReply() {
    if (!replyBody.trim()) return;
    onReply(thread.id, replyBody);
    setReplyBody("");
  }

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[hsl(var(--border))]">
        <h3 className="font-semibold text-[hsl(var(--foreground))]">
          {thread.subject || "Consulta a la clínica"}
        </h3>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 space-y-3 overflow-y-auto min-h-0">
        {thread.messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${
              msg.sender_type === "patient" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-xs md:max-w-md rounded-xl px-3 py-2 ${
                msg.sender_type === "patient"
                  ? "bg-primary-600 text-white"
                  : "bg-slate-100 dark:bg-zinc-800 text-[hsl(var(--foreground))]"
              }`}
            >
              <p className="text-sm">{msg.body}</p>
              <p
                className={`text-xs mt-1 ${
                  msg.sender_type === "patient"
                    ? "text-primary-200"
                    : "text-[hsl(var(--muted-foreground))]"
                }`}
              >
                {msg.sender_type === "staff" && (
                  <span className="font-medium">{msg.sender_name} — </span>
                )}
                {new Date(msg.created_at).toLocaleDateString("es-CO", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Reply input */}
      <div className="p-3 border-t border-[hsl(var(--border))]">
        <div className="flex gap-2">
          <textarea
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleReply();
              }
            }}
            placeholder="Escribe una respuesta..."
            rows={2}
            className="flex-1 px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={handleReply}
            disabled={isSending || !replyBody.trim()}
            className="px-3 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors self-end"
          >
            {isSending ? "..." : "Enviar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortalMessages() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = usePortalMessages();
  const sendMutation = usePortalSendMessage();

  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [newMessageBody, setNewMessageBody] = useState("");

  const threads = data?.pages.flatMap((p) => p.data) ?? [];
  const selectedThread = threads.find((t) => t.id === selectedThreadId);

  async function handleSendNew() {
    if (!newMessageBody.trim()) return;
    await sendMutation.mutateAsync({ body: newMessageBody });
    setNewMessageBody("");
  }

  async function handleReply(threadId: string, body: string) {
    await sendMutation.mutateAsync({ thread_id: threadId, body });
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">
        Mensajes
      </h1>

      {/* New message compose box */}
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4">
        <p className="text-sm font-medium text-[hsl(var(--foreground))] mb-2">
          Nuevo mensaje
        </p>
        <textarea
          value={newMessageBody}
          onChange={(e) => setNewMessageBody(e.target.value)}
          placeholder="Escribe tu consulta a la clínica..."
          rows={3}
          className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        <div className="flex justify-end mt-2">
          <button
            onClick={handleSendNew}
            disabled={sendMutation.isPending || !newMessageBody.trim()}
            className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {sendMutation.isPending ? "Enviando..." : "Enviar mensaje"}
          </button>
        </div>
      </div>

      {/* Thread list + detail panel */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse"
            />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">
            Error al cargar los datos
          </p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      ) : threads.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">
            No tienes mensajes aún
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Thread list */}
          <div className="space-y-2">
            {threads.map((thread) => (
              <ThreadCard
                key={thread.id}
                thread={thread}
                isSelected={selectedThreadId === thread.id}
                onClick={() =>
                  setSelectedThreadId(
                    selectedThreadId === thread.id ? null : thread.id,
                  )
                }
              />
            ))}

            {hasNextPage && (
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="w-full py-2 text-sm text-primary-600 hover:text-primary-700 font-medium disabled:opacity-50 transition-colors"
              >
                {isFetchingNextPage ? "Cargando..." : "Ver más"}
              </button>
            )}
          </div>

          {/* Thread detail panel */}
          {selectedThread ? (
            <div className="hidden md:flex flex-col" style={{ minHeight: 400 }}>
              <ThreadDetail
                thread={selectedThread}
                onReply={handleReply}
                isSending={sendMutation.isPending}
              />
            </div>
          ) : (
            <div className="hidden md:flex items-center justify-center bg-slate-50 dark:bg-zinc-800/50 rounded-xl border border-dashed border-[hsl(var(--border))]">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Selecciona una conversación
              </p>
            </div>
          )}
        </div>
      )}

      {/* Mobile: show selected thread below list */}
      {selectedThread && (
        <div className="md:hidden" style={{ minHeight: 350 }}>
          <ThreadDetail
            thread={selectedThread}
            onReply={handleReply}
            isSending={sendMutation.isPending}
          />
        </div>
      )}
    </div>
  );
}
