"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { QuickReplySelector } from "@/components/whatsapp/quick-reply-selector";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SendMessagePayload {
  body: string;
}

interface SendMessageResponse {
  id: string;
  conversation_id: string;
  direction: "outbound";
  body: string;
  status: string;
  created_at: string;
}

interface SendMessageFormProps {
  conversationId: string;
  onSent: () => void;
}

// ─── SendMessageForm ──────────────────────────────────────────────────────────

export function SendMessageForm({ conversationId, onSent }: SendMessageFormProps) {
  const [body, setBody] = React.useState("");
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    mutationFn: (payload: SendMessagePayload) =>
      apiPost<SendMessageResponse>(
        `/messaging/conversations/${conversationId}/send`,
        payload,
      ),
    onSuccess: () => {
      setBody("");
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-messages", conversationId],
      });
      queryClient.invalidateQueries({
        queryKey: ["whatsapp-conversations"],
      });
      onSent();
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo enviar el mensaje. Inténtalo de nuevo.";
      error("Error al enviar", message);
    },
  });

  function handleSend() {
    const trimmed = body.trim();
    if (!trimmed || isPending) return;
    mutate({ body: trimmed });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleQuickReplySelect(replyBody: string) {
    setBody((prev) => {
      const trimmed = prev.trim();
      return trimmed ? `${trimmed}\n${replyBody}` : replyBody;
    });
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Textarea */}
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Escribe un mensaje… (Ctrl+Enter para enviar)"
        rows={3}
        disabled={isPending}
        className={cn(
          "resize-none text-sm",
          "focus-visible:ring-primary-600",
        )}
        aria-label="Mensaje"
      />

      {/* Controls row */}
      <div className="flex items-center justify-between gap-2">
        {/* Quick reply selector */}
        <QuickReplySelector onSelect={handleQuickReplySelect} />

        {/* Send button */}
        <Button
          type="button"
          size="sm"
          onClick={handleSend}
          disabled={!body.trim() || isPending}
          className="gap-2"
        >
          {isPending ? (
            <span className="flex items-center gap-1.5">
              <svg
                className="animate-spin h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
              Enviando...
            </span>
          ) : (
            <>
              <Send className="h-3.5 w-3.5" />
              Enviar
            </>
          )}
        </Button>
      </div>

      <p className="text-[10px] text-[hsl(var(--muted-foreground))]">
        Ctrl+Enter para enviar rápidamente
      </p>
    </div>
  );
}
