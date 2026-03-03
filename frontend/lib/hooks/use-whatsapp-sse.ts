"use client";

import { useEffect, useRef, useCallback } from "react";
import { getAccessToken } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/api-base-url";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface WhatsAppSSEEvent {
  type: "new_message" | "message_status" | "conversation_update";
  conversation_id: string;
  message_id?: string;
  data: Record<string, unknown>;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;
const BACKOFF_MULTIPLIER = 2;

// ─── useWhatsAppSSE ───────────────────────────────────────────────────────────

/**
 * Opens a Server-Sent Events connection for real-time WhatsApp messages.
 *
 * - Connects to /api/v1/messaging/conversations/stream?token={jwt}
 * - Auto-reconnects on error with exponential backoff
 * - Calls onNewMessage with parsed event data
 * - Cleans up EventSource on unmount
 *
 * @param tenantId - The current tenant ID (used to scope the connection)
 * @param onNewMessage - Callback fired whenever a new SSE event arrives
 */
export function useWhatsAppSSE(
  tenantId: string,
  onNewMessage: (data: WhatsAppSSEEvent) => void,
) {
  const esRef = useRef<EventSource | null>(null);
  const backoffRef = useRef<number>(INITIAL_BACKOFF_MS);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef<boolean>(true);

  // Stable callback ref to avoid reconnecting when the callback changes
  const onNewMessageRef = useRef(onNewMessage);
  onNewMessageRef.current = onNewMessage;

  const connect = useCallback(() => {
    if (!isMountedRef.current || !tenantId) return;

    // Retrieve current JWT access token
    const token = getAccessToken();
    if (!token) {
      // Not authenticated — do not open connection, retry after backoff
      if (isMountedRef.current) {
        retryTimeoutRef.current = setTimeout(connect, backoffRef.current);
      }
      return;
    }

    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}/api/v1/messaging/conversations/stream?token=${encodeURIComponent(token)}`;

    // Close any existing connection before opening a new one
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    const es = new EventSource(url, { withCredentials: true });
    esRef.current = es;

    es.addEventListener("open", () => {
      // Reset backoff on successful connection
      backoffRef.current = INITIAL_BACKOFF_MS;
    });

    es.addEventListener("message", (event: MessageEvent) => {
      if (!isMountedRef.current) return;
      try {
        const parsed = JSON.parse(event.data as string) as WhatsAppSSEEvent;
        onNewMessageRef.current(parsed);
      } catch {
        // Ignore malformed events
      }
    });

    // Named event types from the backend
    es.addEventListener("new_message", (event: MessageEvent) => {
      if (!isMountedRef.current) return;
      try {
        const parsed = JSON.parse(event.data as string) as Omit<
          WhatsAppSSEEvent,
          "type"
        >;
        onNewMessageRef.current({ type: "new_message", ...parsed });
      } catch {
        // Ignore malformed events
      }
    });

    es.addEventListener("message_status", (event: MessageEvent) => {
      if (!isMountedRef.current) return;
      try {
        const parsed = JSON.parse(event.data as string) as Omit<
          WhatsAppSSEEvent,
          "type"
        >;
        onNewMessageRef.current({ type: "message_status", ...parsed });
      } catch {
        // Ignore malformed events
      }
    });

    es.addEventListener("error", () => {
      if (!isMountedRef.current) return;

      // Close the broken connection
      es.close();
      esRef.current = null;

      // Schedule reconnect with exponential backoff
      const delay = backoffRef.current;
      backoffRef.current = Math.min(
        backoffRef.current * BACKOFF_MULTIPLIER,
        MAX_BACKOFF_MS,
      );

      retryTimeoutRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          connect();
        }
      }, delay);
    });
  }, [tenantId]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;

      // Clear any pending reconnect timer
      if (retryTimeoutRef.current !== null) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }

      // Close the EventSource connection
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [connect]);
}
