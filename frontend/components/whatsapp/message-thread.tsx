"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ConversationHeader } from "@/components/whatsapp/conversation-header";
import { SendMessageForm } from "@/components/whatsapp/send-message-form";
import { useWhatsAppSSE } from "@/lib/hooks/use-whatsapp-sse";
import { useAuthStore } from "@/lib/hooks/use-auth";
import type { WhatsAppConversation } from "@/components/whatsapp/conversation-list";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface WhatsAppMessage {
  id: string;
  conversation_id: string;
  direction: "inbound" | "outbound";
  body: string;
  status: "sent" | "delivered" | "read" | "failed";
  sender_name: string | null;
  media_url: string | null;
  created_at: string;
}

interface MessageListResponse {
  items: WhatsAppMessage[];
  total: number;
  page: number;
  page_size: number;
}

interface ConversationDetailResponse extends WhatsAppConversation {
  // extends with any detail fields the API provides
}

interface MessageThreadProps {
  conversationId: string;
  onBackToList: () => void;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

const conversationDetailKey = (id: string) =>
  ["whatsapp-conversation", id] as const;
const conversationMessagesKey = (id: string, page: number) =>
  ["whatsapp-messages", id, page] as const;

// ─── MessageThread ────────────────────────────────────────────────────────────

export function MessageThread({ conversationId, onBackToList }: MessageThreadProps) {
  const queryClient = useQueryClient();
  const tenant = useAuthStore((s) => s.tenant);
  const bottomRef = React.useRef<HTMLDivElement>(null);
  const [page] = React.useState(1);

  // Fetch conversation detail (for header)
  const { data: conversation } = useQuery({
    queryKey: conversationDetailKey(conversationId),
    queryFn: () =>
      apiGet<ConversationDetailResponse>(`/messaging/conversations/${conversationId}`),
    staleTime: 60_000,
  });

  // Fetch messages
  const {
    data: messagesData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: conversationMessagesKey(conversationId, page),
    queryFn: () =>
      apiGet<MessageListResponse>(
        `/messaging/conversations/${conversationId}/messages?page=${page}&page_size=50`,
      ),
    staleTime: 15_000,
  });

  // SSE: real-time new messages
  useWhatsAppSSE(tenant?.id ?? "", (event) => {
    if (event.conversation_id === conversationId) {
      queryClient.invalidateQueries({
        queryKey: conversationMessagesKey(conversationId, page),
      });
    }
  });

  // Auto-scroll to bottom when messages change
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messagesData?.items]);

  // Also scroll on initial load
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "instant" });
  }, [conversationId]);

  function handleMessageSent() {
    queryClient.invalidateQueries({
      queryKey: conversationMessagesKey(conversationId, page),
    });
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Mobile back button + header */}
      <div className="shrink-0 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2 px-2 pt-2 md:hidden">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBackToList}
            className="gap-1.5"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
        </div>
        {conversation && (
          <ConversationHeader conversation={conversation} />
        )}
        {!conversation && (
          <div className="flex items-center gap-3 px-4 py-3">
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="space-y-1.5">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {isLoading && (
          <>
            <MessageSkeleton direction="inbound" />
            <MessageSkeleton direction="outbound" />
            <MessageSkeleton direction="inbound" />
            <MessageSkeleton direction="outbound" />
          </>
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-[hsl(var(--muted-foreground))]">
            <RefreshCw className="h-5 w-5" />
            <p className="text-sm">No se pudieron cargar los mensajes</p>
          </div>
        )}

        {!isLoading && !isError && messagesData?.items.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-[hsl(var(--muted-foreground))]">
            <p className="text-sm">Sin mensajes en esta conversación</p>
          </div>
        )}

        {!isLoading &&
          !isError &&
          messagesData?.items.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

        {/* Scroll anchor */}
        <div ref={bottomRef} />
      </div>

      {/* Send message form */}
      <div className="shrink-0 border-t border-[hsl(var(--border))] p-3">
        <SendMessageForm
          conversationId={conversationId}
          onSent={handleMessageSent}
        />
      </div>
    </div>
  );
}

// ─── MessageBubble ────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: WhatsAppMessage }) {
  const isOutbound = message.direction === "outbound";
  const time = new Date(message.created_at).toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={cn(
        "flex",
        isOutbound ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2.5 shadow-sm",
          isOutbound
            ? "bg-primary-600 text-white rounded-br-sm"
            : "bg-[hsl(var(--muted))] text-foreground rounded-bl-sm",
        )}
      >
        {/* Sender name (for outbound, show staff name) */}
        {isOutbound && message.sender_name && (
          <p className="text-[10px] font-medium opacity-75 mb-0.5">
            {message.sender_name}
          </p>
        )}

        {/* Message body */}
        <p className="text-sm whitespace-pre-wrap break-words">{message.body}</p>

        {/* Media */}
        {message.media_url && (
          <a
            href={message.media_url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "block mt-1.5 text-xs underline",
              isOutbound ? "text-white/80" : "text-primary-600",
            )}
          >
            Ver adjunto
          </a>
        )}

        {/* Timestamp */}
        <p
          className={cn(
            "text-[10px] mt-1 text-right",
            isOutbound ? "text-white/60" : "text-[hsl(var(--muted-foreground))]",
          )}
        >
          {time}
          {isOutbound && message.status === "read" && (
            <span className="ml-1">✓✓</span>
          )}
          {isOutbound && message.status === "delivered" && (
            <span className="ml-1">✓✓</span>
          )}
          {isOutbound && message.status === "sent" && (
            <span className="ml-1">✓</span>
          )}
        </p>
      </div>
    </div>
  );
}

// ─── MessageSkeleton ──────────────────────────────────────────────────────────

function MessageSkeleton({ direction }: { direction: "inbound" | "outbound" }) {
  return (
    <div className={cn("flex", direction === "outbound" ? "justify-end" : "justify-start")}>
      <Skeleton
        className={cn(
          "h-12 rounded-2xl",
          direction === "outbound" ? "w-48" : "w-56",
        )}
      />
    </div>
  );
}
