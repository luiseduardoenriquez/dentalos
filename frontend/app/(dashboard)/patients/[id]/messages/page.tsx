"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight, MessageSquarePlus, MessageCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  useMessageThreads,
  useThreadMessages,
  useCreateThread,
  useSendMessage,
  useMarkThreadRead,
  type ThreadResponse,
  type MessageResponse,
} from "@/lib/hooks/use-messaging";

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function MessagesListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-80 rounded-xl" />
      </div>
    </div>
  );
}

// ─── Thread Card ──────────────────────────────────────────────────────────────

function ThreadCard({
  thread,
  isSelected,
  onClick,
}: {
  thread: ThreadResponse;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border p-4 transition-colors ${
        isSelected
          ? "border-primary-400 bg-primary-50 dark:border-primary-600 dark:bg-primary-900/20"
          : "border-[hsl(var(--border))] hover:border-primary-300 dark:hover:border-primary-700"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-sm text-foreground truncate">
            {thread.subject || "Conversación"}
          </p>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
            {new Date(thread.last_message_at).toLocaleDateString("es-CO", {
              day: "numeric",
              month: "short",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={thread.status === "open" ? "success" : "secondary"} className="text-[10px]">
            {thread.status === "open" ? "Abierto" : thread.status === "closed" ? "Cerrado" : "Archivado"}
          </Badge>
          {thread.unread_count > 0 && (
            <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs rounded-full bg-primary-600 text-white">
              {thread.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

// ─── Message Bubble ───────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: MessageResponse }) {
  const isStaff = message.sender_type === "staff";

  return (
    <div className={`flex ${isStaff ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-xs md:max-w-md rounded-xl px-3 py-2 ${
          isStaff
            ? "bg-primary-600 text-white"
            : "bg-slate-100 dark:bg-zinc-800 text-foreground"
        }`}
      >
        <p className="text-sm">{message.body}</p>
        <p
          className={`text-xs mt-1 ${
            isStaff ? "text-primary-200" : "text-[hsl(var(--muted-foreground))]"
          }`}
        >
          {message.sender_name && (
            <span className="font-medium">{message.sender_name} — </span>
          )}
          {new Date(message.created_at).toLocaleDateString("es-CO", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientMessagesPage() {
  const params = useParams<{ id: string }>();
  const patientId = params.id;

  const { data: patient } = usePatient(patientId);
  const { data: threadsData, isLoading, isError } = useMessageThreads(patientId);
  const createThread = useCreateThread();
  const sendMessage = useSendMessage();
  const markRead = useMarkThreadRead();

  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [newSubject, setNewSubject] = useState("");
  const [newMessage, setNewMessage] = useState("");
  const [replyBody, setReplyBody] = useState("");
  const [showNewThread, setShowNewThread] = useState(false);

  const threads = threadsData?.data ?? [];
  const selectedThread = threads.find((t) => t.id === selectedThreadId);

  const { data: messagesData } = useThreadMessages(selectedThreadId);
  const messages = messagesData?.data ?? [];

  function handleSelectThread(threadId: string) {
    setSelectedThreadId(threadId);
    markRead.mutate(threadId);
  }

  function handleCreateThread() {
    if (!newMessage.trim()) return;
    createThread.mutate(
      { patient_id: patientId, subject: newSubject.trim() || undefined, initial_message: newMessage },
      {
        onSuccess: () => {
          setNewSubject("");
          setNewMessage("");
          setShowNewThread(false);
        },
      },
    );
  }

  function handleReply() {
    if (!replyBody.trim() || !selectedThreadId) return;
    sendMessage.mutate(
      { threadId: selectedThreadId, body: replyBody },
      { onSuccess: () => setReplyBody("") },
    );
  }

  if (isLoading) return <MessagesListSkeleton />;

  const patientName = patient ? `${patient.first_name} ${patient.last_name}` : "Paciente";

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]" aria-label="Ruta de navegación">
        <Link href="/patients" className="hover:text-foreground transition-colors">Pacientes</Link>
        <ChevronRight className="h-4 w-4" />
        <Link href={`/patients/${patientId}`} className="hover:text-foreground transition-colors">{patientName}</Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Mensajes</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Mensajes</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Comunicación con el paciente.</p>
        </div>
        <Button onClick={() => setShowNewThread((p) => !p)}>
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          Nuevo mensaje
        </Button>
      </div>

      {/* New thread compose */}
      {showNewThread && (
        <div className="rounded-xl border border-[hsl(var(--border))] p-4 space-y-3">
          <input
            type="text"
            value={newSubject}
            onChange={(e) => setNewSubject(e.target.value)}
            placeholder="Asunto (opcional)"
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-primary-600"
          />
          <textarea
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Escribe tu mensaje..."
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-transparent text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary-600"
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowNewThread(false)}>Cancelar</Button>
            <Button size="sm" onClick={handleCreateThread} disabled={createThread.isPending || !newMessage.trim()}>
              {createThread.isPending ? "Enviando..." : "Enviar"}
            </Button>
          </div>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <EmptyState
          icon={AlertCircle}
          title="Error al cargar mensajes"
          description="No se pudieron cargar los mensajes. Intenta de nuevo."
        />
      )}

      {/* Thread list + detail */}
      {!isError && threads.length === 0 && !showNewThread ? (
        <EmptyState
          icon={MessageCircle}
          title="Sin mensajes"
          description="No hay hilos de mensajes con este paciente."
        />
      ) : threads.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Thread list */}
          <div className="space-y-2">
            {threads.map((thread) => (
              <ThreadCard
                key={thread.id}
                thread={thread}
                isSelected={selectedThreadId === thread.id}
                onClick={() => handleSelectThread(thread.id)}
              />
            ))}
          </div>

          {/* Message detail */}
          {selectedThread ? (
            <div className="rounded-xl border border-[hsl(var(--border))] flex flex-col" style={{ minHeight: 400 }}>
              <div className="px-4 py-3 border-b border-[hsl(var(--border))]">
                <h3 className="font-semibold text-foreground">
                  {selectedThread.subject || "Conversación"}
                </h3>
              </div>
              <div className="flex-1 p-4 space-y-3 overflow-y-auto min-h-0">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
              </div>
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
                    className="flex-1 px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-transparent text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary-600"
                  />
                  <Button
                    size="sm"
                    onClick={handleReply}
                    disabled={sendMessage.isPending || !replyBody.trim()}
                    className="self-end"
                  >
                    {sendMessage.isPending ? "..." : "Enviar"}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="hidden md:flex items-center justify-center rounded-xl border border-dashed border-[hsl(var(--border))] bg-slate-50 dark:bg-zinc-800/50" style={{ minHeight: 400 }}>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Selecciona una conversación</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
