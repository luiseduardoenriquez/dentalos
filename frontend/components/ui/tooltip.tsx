"use client";

import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

// ─── Root Primitives ──────────────────────────────────────────────────────────

/**
 * Wrap your app or layout with TooltipProvider once.
 * Default delay: 300ms — reduces jarring tooltips appearing on fast cursor movement.
 */
const TooltipProvider = TooltipPrimitive.Provider;
const Tooltip = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;

// ─── Content ──────────────────────────────────────────────────────────────────

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 overflow-hidden rounded-md",
        "bg-foreground text-[hsl(var(--background))] dark:bg-[hsl(var(--popover))] dark:text-[hsl(var(--popover-foreground))]",
        "px-3 py-1.5 text-xs font-medium shadow-md",
        // Animations
        "animate-in fade-in-0 zoom-in-95",
        "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
        "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
        "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
        className,
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

// ─── Convenience wrapper ──────────────────────────────────────────────────────

/**
 * Convenience component: wraps Tooltip + Trigger + Content in one.
 *
 * Usage:
 * <SimpleTooltip content="Guardar cambios">
 *   <Button>...</Button>
 * </SimpleTooltip>
 */
interface SimpleTooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: React.ComponentPropsWithoutRef<typeof TooltipContent>["side"];
  delayDuration?: number;
}

function SimpleTooltip({ content, children, side, delayDuration = 300 }: SimpleTooltipProps) {
  return (
    <Tooltip delayDuration={delayDuration}>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{content}</TooltipContent>
    </Tooltip>
  );
}

export { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent, SimpleTooltip };
