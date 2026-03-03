"use client";

import * as React from "react";
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// ─── Size variants ────────────────────────────────────────────────────────────

const avatarVariants = cva(
  "relative flex shrink-0 overflow-hidden rounded-full",
  {
    variants: {
      size: {
        sm: "h-8 w-8",
        default: "h-10 w-10",
        lg: "h-12 w-12",
      },
    },
    defaultVariants: {
      size: "default",
    },
  },
);

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AvatarProps
  extends React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>,
    VariantProps<typeof avatarVariants> {}

// ─── Avatar Root ──────────────────────────────────────────────────────────────

const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  AvatarProps
>(({ className, size, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn(avatarVariants({ size }), className)}
    {...props}
  />
));
Avatar.displayName = AvatarPrimitive.Root.displayName;

// ─── Avatar Image ─────────────────────────────────────────────────────────────

const AvatarImage = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={cn("aspect-square h-full w-full object-cover", className)}
    {...props}
  />
));
AvatarImage.displayName = AvatarPrimitive.Image.displayName;

// ─── Avatar Fallback ──────────────────────────────────────────────────────────

const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      "flex h-full w-full items-center justify-center rounded-full",
      "bg-primary-100 text-primary-700 font-semibold text-sm",
      "dark:bg-primary-900/40 dark:text-primary-300",
      className,
    )}
    {...props}
  />
));
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName;

// ─── Avatar Status Indicator ─────────────────────────────────────────────────

type AvatarStatusVariant = "online" | "offline" | "busy" | "away";

const statusColorMap: Record<AvatarStatusVariant, string> = {
  online: "bg-green-500",
  offline: "bg-gray-400",
  busy: "bg-red-500",
  away: "bg-amber-500",
};

interface AvatarStatusProps {
  variant: AvatarStatusVariant;
  className?: string;
}

function AvatarStatus({ variant, className }: AvatarStatusProps) {
  return (
    <span
      className={cn(
        "absolute bottom-0 right-0 block h-2.5 w-2.5 rounded-full ring-2 ring-white dark:ring-zinc-900",
        statusColorMap[variant],
        className,
      )}
      aria-label={variant}
    />
  );
}

export { Avatar, AvatarImage, AvatarFallback, AvatarStatus, type AvatarStatusVariant };
