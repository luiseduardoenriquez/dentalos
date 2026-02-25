"use client";

import * as React from "react";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button, type ButtonProps } from "@/components/ui/button";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface EmptyStateAction {
  label: string;
  onClick?: () => void;
  href?: string;
  variant?: ButtonProps["variant"];
}

export interface EmptyStateProps {
  /** Icon from lucide-react */
  icon?: LucideIcon;
  /** Main title */
  title: string;
  /** Supporting description */
  description?: string;
  /** Optional CTA action */
  action?: EmptyStateAction;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center py-16 px-6",
        className,
      )}
    >
      {Icon && (
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[hsl(var(--muted))] mb-4">
          <Icon className="h-8 w-8 text-[hsl(var(--muted-foreground))]" />
        </div>
      )}

      <h3 className="text-base font-semibold text-foreground">{title}</h3>

      {description && (
        <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))] max-w-sm">
          {description}
        </p>
      )}

      {action && (
        <div className="mt-6">
          {action.href ? (
            <Button variant={action.variant ?? "default"} asChild>
              <a href={action.href}>{action.label}</a>
            </Button>
          ) : (
            <Button variant={action.variant ?? "default"} onClick={action.onClick}>
              {action.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
