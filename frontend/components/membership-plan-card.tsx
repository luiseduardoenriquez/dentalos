"use client";

/**
 * MembershipPlanCard — Reusable card for displaying a membership plan.
 *
 * Shows: plan name, price, discount badge, benefits list, and an action button.
 * Used in: patient membership subscription page and settings plans page.
 */

import * as React from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Pencil } from "lucide-react";
import { formatCurrency, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Plan {
  id: string;
  name: string;
  description: string | null;
  price_monthly: number;
  discount_percentage: number;
  benefits: string[];
  is_active?: boolean;
}

export interface MembershipPlanCardProps {
  plan: Plan;
  /** Highlight this card as selected */
  selected?: boolean;
  /** Label for the primary action button */
  actionLabel?: string;
  /** Called when the primary action button is clicked */
  onAction?: (planId: string) => void;
  /** Optional secondary edit action (for settings pages) */
  onEdit?: (planId: string) => void;
  /** Disable the action button (e.g. while submitting) */
  disabled?: boolean;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function MembershipPlanCard({
  plan,
  selected = false,
  actionLabel = "Seleccionar",
  onAction,
  onEdit,
  disabled = false,
  className,
}: MembershipPlanCardProps) {
  return (
    <Card
      className={cn(
        "flex flex-col transition-shadow",
        selected
          ? "border-primary-600 ring-2 ring-primary-600/20 shadow-md"
          : "hover:shadow-sm",
        !plan.is_active && plan.is_active !== undefined && "opacity-60",
        className,
      )}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{plan.name}</CardTitle>
          <div className="flex gap-1 flex-wrap justify-end">
            {plan.discount_percentage > 0 && (
              <Badge
                variant="outline"
                className="text-xs text-green-700 border-green-300 bg-green-50 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400 shrink-0"
              >
                -{plan.discount_percentage}%
              </Badge>
            )}
            {plan.is_active === false && (
              <Badge variant="secondary" className="text-xs shrink-0">
                Archivado
              </Badge>
            )}
          </div>
        </div>

        {plan.description && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2 mt-1">
            {plan.description}
          </p>
        )}
      </CardHeader>

      <CardContent className="flex-1 space-y-4 pb-3">
        {/* Price */}
        <div>
          <span className="text-2xl font-bold tabular-nums">
            {formatCurrency(plan.price_monthly)}
          </span>
          <span className="text-sm text-[hsl(var(--muted-foreground))]">/mes</span>
        </div>

        {/* Benefits */}
        {plan.benefits.length > 0 && (
          <ul className="space-y-1.5">
            {plan.benefits.map((benefit) => (
              <li key={benefit} className="flex items-start gap-2 text-sm">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                <span className="text-[hsl(var(--muted-foreground))]">{benefit}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      <CardFooter className="flex gap-2 pt-0">
        {onAction && (
          <Button
            className="flex-1"
            variant={selected ? "default" : "outline"}
            onClick={() => onAction(plan.id)}
            disabled={disabled}
            size="sm"
          >
            {selected ? (
              <>
                <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                Seleccionado
              </>
            ) : (
              actionLabel
            )}
          </Button>
        )}
        {onEdit && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(plan.id)}
            disabled={disabled}
            title="Editar plan"
          >
            <Pencil className="h-4 w-4" />
            <span className="sr-only">Editar</span>
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
