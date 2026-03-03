"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Clock, UserCheck } from "lucide-react";
import { formatTime, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SuggestedFillCardProps {
  patientName: string;
  reason: string;
  slotStart: string;
  slotEnd: string;
  doctorName: string;
  onInvite: () => void;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function SuggestedFillCard({
  patientName,
  reason,
  slotStart,
  slotEnd,
  doctorName,
  onInvite,
  className,
}: SuggestedFillCardProps) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-3 rounded-lg border border-[hsl(var(--border))]",
        "bg-[hsl(var(--card))] p-3 shadow-sm",
        className,
      )}
    >
      <div className="min-w-0 space-y-1">
        {/* Patient name */}
        <p className="text-sm font-semibold text-foreground truncate">
          {patientName}
        </p>

        {/* Time slot */}
        <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
          <Clock className="h-3 w-3 shrink-0" />
          <span>
            {formatTime(slotStart)} – {formatTime(slotEnd)}
          </span>
          <span className="text-[hsl(var(--muted-foreground))]/50">·</span>
          <span className="truncate">{doctorName}</span>
        </div>

        {/* Reason */}
        <p className="text-xs text-primary-600 dark:text-primary-400 truncate">
          {reason}
        </p>
      </div>

      {/* Action */}
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={onInvite}
        className="shrink-0 h-7 px-2 text-xs gap-1"
      >
        <UserCheck className="h-3 w-3" />
        Invitar
      </Button>
    </div>
  );
}
