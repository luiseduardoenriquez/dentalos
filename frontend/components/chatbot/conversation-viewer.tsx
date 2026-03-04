"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Bot, User, Loader2, X } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type MessageRole = "user" | "bot" | "system";

interface ConversationMessage {
  id: string;
  role: MessageRole;
  content: string;
  intent?: string | null;
  intent_confidence?: number | null;
  created_at: string;
}

interface ConversationDetail {
  id: string;
  channel: string;
  patient_name: string | null;
  patient_phone: string | null;
  status: string;
  started_at: string;
  messages: ConversationMessage[];
}

// ─── Intent badge ─────────────────────────────────────────────────────────────

function IntentBadge({ intent, confidence }: { intent: string; confidence?: number | null }) {
  return (
    <Badge
      variant="outline"
      className="text-xs bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700"
    >
      {intent}
      {confidence != null && (
        <span className="ml-1 opacity-70">({(confidence * 100).toFixed(0)}%)</span>
      )}
    </Badge>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: ConversationMessage }) {
  if (message.role === "system") {
    return (
      <div className="flex justify-center my-2">
        <span className="inline-block rounded-full bg-[hsl(var(--muted))] px-3 py-1 text-xs text-[hsl(var(--muted-foreground))]">
          {message.content}
        </span>
      </div>
    );
  }

  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-2 max-w-[85%]",
        isUser ? "ml-auto flex-row-reverse" : "mr-auto",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary-100 dark:bg-primary-900/30"
            : "bg-slate-100 dark:bg-zinc-800",
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-primary-600" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-slate-500 dark:text-zinc-400" />
        )}
      </div>

      {/* Content */}
      <div className="space-y-1">
        <div
          className={cn(
            "rounded-2xl px-3 py-2 text-sm",
            isUser
              ? "rounded-tr-sm bg-primary-600 text-white"
              : "rounded-tl-sm bg-white dark:bg-zinc-800 border border-[hsl(var(--border))] text-foreground",
          )}
        >
          {message.content}
        </div>

        {/* Intent badge for bot messages */}
        {!isUser && message.intent && (
          <IntentBadge
            intent={message.intent}
            confidence={message.intent_confidence}
          />
        )}

        {/* Timestamp */}
        <p
          className={cn(
            "text-xs text-[hsl(var(--muted-foreground))]",
            isUser ? "text-right" : "text-left",
          )}
        >
          {formatDateTime(message.created_at)}
        </p>
      </div>
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function ConversationSkeleton() {
  return (
    <div className="space-y-3 p-4">
      {[1, 2, 3, 4].map((i) => (
        <Skeleton
          key={i}
          className={cn("h-12 rounded-2xl", i % 2 === 0 ? "ml-auto w-2/3" : "w-2/3")}
        />
      ))}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface ConversationViewerProps {
  conversationId: string;
  onClose: () => void;
}

export function ConversationViewer({ conversationId, onClose }: ConversationViewerProps) {
  const queryClient = useQueryClient();
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["chatbot-conversation", conversationId],
    queryFn: () => apiGet<ConversationDetail>(`/chatbot/conversations/${conversationId}`),
    staleTime: 30_000,
  });

  // Scroll to bottom when messages load
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [data?.messages]);

  const { mutate: escalate, isPending: isEscalating } = useMutation({
    mutationFn: () => apiPost<void>(`/chatbot/conversations/${conversationId}/escalate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chatbot-conversation", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["chatbot-conversations"] });
    },
  });

  const { mutate: resolve, isPending: isResolving } = useMutation({
    mutationFn: () => apiPost<void>(`/chatbot/conversations/${conversationId}/resolve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chatbot-conversation", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["chatbot-conversations"] });
    },
  });

  const canEscalate = data?.status === "active";
  const canResolve = data?.status === "active" || data?.status === "escalated";

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg p-0 overflow-hidden flex flex-col" style={{ maxHeight: "85vh" }}>
        {/* Header */}
        <DialogHeader className="px-5 py-4 border-b border-[hsl(var(--border))] shrink-0">
          <div className="flex items-center justify-between pr-6">
            <DialogTitle className="text-base">
              {data?.patient_name ?? data?.patient_phone ?? "Conversación"}
            </DialogTitle>
            {data && (
              <Badge
                variant="outline"
                className={cn(
                  "text-xs",
                  data.status === "active" &&
                    "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300",
                  data.status === "escalated" &&
                    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300",
                  data.status === "resolved" &&
                    "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
                )}
              >
                {data.status === "active"
                  ? "Activo"
                  : data.status === "escalated"
                  ? "Escalado"
                  : "Resuelto"}
              </Badge>
            )}
          </div>
          {data && (
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
              Canal: {data.channel} · Iniciado: {formatDateTime(data.started_at)}
            </p>
          )}
        </DialogHeader>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50 dark:bg-zinc-900/50">
          {isLoading ? (
            <ConversationSkeleton />
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <p className="text-sm text-red-600 dark:text-red-400">
                No se pudo cargar la conversación.
              </p>
            </div>
          ) : (data?.messages ?? []).length === 0 ? (
            <p className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
              Esta conversación no tiene mensajes.
            </p>
          ) : (
            (data?.messages ?? []).map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Action buttons */}
        {data && (canEscalate || canResolve) && (
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[hsl(var(--border))] shrink-0 bg-white dark:bg-zinc-900">
            {canEscalate && (
              <Button
                variant="outline"
                size="sm"
                className="text-amber-600 border-amber-200 hover:bg-amber-50 dark:text-amber-400"
                disabled={isEscalating}
                onClick={() => escalate()}
              >
                {isEscalating ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <AlertTriangle className="mr-1.5 h-3.5 w-3.5" />
                )}
                Escalar
              </Button>
            )}
            {canResolve && (
              <Button
                variant="outline"
                size="sm"
                className="text-green-600 border-green-200 hover:bg-green-50 dark:text-green-400"
                disabled={isResolving}
                onClick={() => resolve()}
              >
                {isResolving ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                )}
                Resolver
              </Button>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
