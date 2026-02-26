"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X, Bell, CheckCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
  type NotificationResponse,
} from "@/lib/hooks/use-notifications";
import { NotificationItem } from "./notification-item";
import { useRouter } from "next/navigation";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface NotificationDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ─── Component ───────────────────────────────────────────────────────────────

export function NotificationDrawer({ open, onOpenChange }: NotificationDrawerProps) {
  const router = useRouter();
  const [filter, setFilter] = React.useState<"all" | "unread">("all");
  const status = filter === "unread" ? "unread" : undefined;

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useNotifications(status);

  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  const notifications = data?.pages.flatMap((page) => page.data) ?? [];
  const totalUnread = data?.pages[0]?.pagination.total_unread ?? 0;

  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Infinite scroll observer
  const observerRef = React.useRef<IntersectionObserver | null>(null);
  const sentinelRef = React.useCallback(
    (node: HTMLDivElement | null) => {
      if (observerRef.current) observerRef.current.disconnect();
      if (!node) return;

      observerRef.current = new IntersectionObserver((entries) => {
        if (entries[0]?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      });
      observerRef.current.observe(node);
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage],
  );

  function handleNotificationClick(notification: NotificationResponse) {
    // Mark as read
    if (!notification.read_at) {
      markRead.mutate(notification.id);
    }

    // Navigate if action_url exists
    if (notification.meta_data?.action_url) {
      onOpenChange(false);
      router.push(notification.meta_data.action_url);
    }
  }

  function handleMarkAllRead() {
    markAllRead.mutate(undefined);
  }

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        {/* Overlay */}
        <DialogPrimitive.Overlay
          className={cn(
            "fixed inset-0 z-50 bg-black/40",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
          )}
        />

        {/* Panel — slides from right */}
        <DialogPrimitive.Content
          className={cn(
            "fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col",
            "border-l border-[hsl(var(--border))] bg-[hsl(var(--background))] shadow-xl",
            "data-[state=open]:animate-in data-[state=open]:slide-in-from-right",
            "data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right",
            "duration-200",
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-3">
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-foreground" />
              <h2 className="text-base font-semibold text-foreground">
                Notificaciones
              </h2>
              {totalUnread > 0 && (
                <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-600 px-1.5 text-[11px] font-bold text-white">
                  {totalUnread > 99 ? "99+" : totalUnread}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1">
              {totalUnread > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllRead}
                  disabled={markAllRead.isPending}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium",
                    "text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-950/30",
                    "transition-colors duration-150",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                  )}
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  Marcar todas
                </button>
              )}
              <DialogPrimitive.Close
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-md",
                  "text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))]",
                  "transition-colors duration-150",
                )}
              >
                <X className="h-4 w-4" />
                <span className="sr-only">Cerrar</span>
              </DialogPrimitive.Close>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="flex border-b border-[hsl(var(--border))] px-4">
            <button
              type="button"
              onClick={() => setFilter("all")}
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors duration-150",
                filter === "all"
                  ? "border-b-2 border-primary-600 text-primary-600"
                  : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
              )}
            >
              Todas
            </button>
            <button
              type="button"
              onClick={() => setFilter("unread")}
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors duration-150",
                filter === "unread"
                  ? "border-b-2 border-primary-600 text-primary-600"
                  : "text-[hsl(var(--muted-foreground))] hover:text-foreground",
              )}
            >
              Sin leer
            </button>
          </div>

          {/* Notification list */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="space-y-1 p-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 rounded-lg px-3 py-3 animate-pulse"
                  >
                    <div className="h-9 w-9 rounded-full bg-[hsl(var(--muted))]" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-3/4 rounded bg-[hsl(var(--muted))]" />
                      <div className="h-3 w-full rounded bg-[hsl(var(--muted))]" />
                      <div className="h-3 w-1/4 rounded bg-[hsl(var(--muted))]" />
                    </div>
                  </div>
                ))}
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
                <Bell className="h-12 w-12 text-[hsl(var(--muted-foreground))]/40 mb-3" />
                <p className="text-sm font-medium text-foreground">
                  No hay notificaciones
                </p>
                <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                  {filter === "unread"
                    ? "No tienes notificaciones sin leer."
                    : "Aquí aparecerán tus notificaciones."}
                </p>
              </div>
            ) : (
              <div className="p-2 space-y-0.5">
                {notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onClick={handleNotificationClick}
                  />
                ))}
                {/* Infinite scroll sentinel */}
                <div ref={sentinelRef} className="h-1" />
                {isFetchingNextPage && (
                  <div className="flex justify-center py-3">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
                  </div>
                )}
              </div>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
