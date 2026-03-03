"use client";

import * as React from "react";
import { MessageSquare } from "lucide-react";
import { ConversationList } from "@/components/whatsapp/conversation-list";
import { MessageThread } from "@/components/whatsapp/message-thread";
import { cn } from "@/lib/utils";

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * WhatsApp Chat page.
 *
 * Split layout:
 * - Left panel (~1/3): conversation list
 * - Right panel (~2/3): message thread
 *
 * On mobile: shows either the list OR the thread, not both.
 */
export default function WhatsAppPage() {
  const [selectedConversationId, setSelectedConversationId] = React.useState<
    string | null
  >(null);

  // On mobile, when a conversation is selected, hide the list
  const showListOnMobile = selectedConversationId === null;

  function handleSelectConversation(id: string) {
    setSelectedConversationId(id);
  }

  function handleBackToList() {
    setSelectedConversationId(null);
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Conversation List (left panel) ── */}
      <div
        className={cn(
          "flex flex-col border-r border-[hsl(var(--border))] overflow-hidden",
          "w-full md:w-1/3 md:flex",
          showListOnMobile ? "flex" : "hidden",
        )}
      >
        <ConversationList
          selectedId={selectedConversationId}
          onSelectConversation={handleSelectConversation}
        />
      </div>

      {/* ── Message Thread (right panel) ── */}
      <div
        className={cn(
          "flex flex-col flex-1 overflow-hidden",
          "w-full md:flex",
          selectedConversationId !== null ? "flex" : "hidden md:flex",
        )}
      >
        {selectedConversationId ? (
          <MessageThread
            conversationId={selectedConversationId}
            onBackToList={handleBackToList}
          />
        ) : (
          <EmptyThreadState />
        )}
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyThreadState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-[hsl(var(--muted-foreground))]">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[hsl(var(--muted))]">
        <MessageSquare className="h-8 w-8 opacity-60" />
      </div>
      <div className="text-center">
        <p className="text-base font-medium">Selecciona una conversación</p>
        <p className="text-sm mt-1">
          Elige un chat de la lista para ver los mensajes
        </p>
      </div>
    </div>
  );
}
