"use client";

import {
  Bell,
  Calendar,
  DollarSign,
  FileText,
  MessageSquare,
  Package,
  Settings,
  ShieldCheck,
  UserPlus,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { NotificationResponse, NotificationType } from "@/lib/hooks/use-notifications";

// ─── Icon Mapping ────────────────────────────────────────────────────────────

const NOTIFICATION_ICONS: Record<NotificationType, React.ElementType> = {
  appointment_reminder: Calendar,
  appointment_confirmed: Calendar,
  appointment_cancelled: XCircle,
  new_patient: UserPlus,
  payment_received: DollarSign,
  payment_overdue: DollarSign,
  treatment_plan_approved: FileText,
  consent_signed: ShieldCheck,
  message_received: MessageSquare,
  inventory_alert: Package,
  system_update: Settings,
};

const NOTIFICATION_COLORS: Record<NotificationType, string> = {
  appointment_reminder: "text-primary-600",
  appointment_confirmed: "text-green-600",
  appointment_cancelled: "text-destructive-600",
  new_patient: "text-blue-600",
  payment_received: "text-green-600",
  payment_overdue: "text-orange-600",
  treatment_plan_approved: "text-primary-600",
  consent_signed: "text-green-600",
  message_received: "text-blue-600",
  inventory_alert: "text-orange-600",
  system_update: "text-slate-600",
};

// ─── Relative Time ───────────────────────────────────────────────────────────

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "ahora";
  if (diffMin < 60) return `hace ${diffMin} min`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `hace ${diffHr} h`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays < 7) return `hace ${diffDays} d`;
  return new Date(dateStr).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
  });
}

// ─── Component ───────────────────────────────────────────────────────────────

export interface NotificationItemProps {
  notification: NotificationResponse;
  onClick?: (notification: NotificationResponse) => void;
}

export function NotificationItem({ notification, onClick }: NotificationItemProps) {
  const Icon = NOTIFICATION_ICONS[notification.type] ?? Bell;
  const iconColor = NOTIFICATION_COLORS[notification.type] ?? "text-slate-600";
  const isUnread = notification.read_at === null;

  return (
    <button
      type="button"
      onClick={() => onClick?.(notification)}
      className={cn(
        "flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left transition-colors duration-150",
        "hover:bg-[hsl(var(--muted))]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
        isUnread && "bg-primary-50/50 dark:bg-primary-950/20",
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
          "bg-[hsl(var(--muted))]",
        )}
      >
        <Icon className={cn("h-4.5 w-4.5", iconColor)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p
            className={cn(
              "text-sm leading-tight truncate",
              isUnread ? "font-semibold text-foreground" : "font-medium text-foreground",
            )}
          >
            {notification.title}
          </p>
          {/* Unread dot */}
          {isUnread && (
            <span
              className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary-600"
              aria-label="Sin leer"
            />
          )}
        </div>
        <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))] line-clamp-2">
          {notification.body}
        </p>
        <p className="mt-1 text-[11px] text-[hsl(var(--muted-foreground))]">
          {relativeTime(notification.created_at)}
        </p>
      </div>
    </button>
  );
}
