"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// ─── Variants ─────────────────────────────────────────────────────────────────

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium",
    "transition-colors duration-150",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  ],
  {
    variants: {
      variant: {
        default: [
          "bg-primary-600 text-white shadow",
          "hover:bg-primary-700 active:bg-primary-800",
          "dark:bg-primary-600 dark:hover:bg-primary-500",
        ],
        secondary: [
          "bg-secondary-600 text-white shadow",
          "hover:bg-secondary-700 active:bg-secondary-800",
          "dark:bg-secondary-600 dark:hover:bg-secondary-500",
        ],
        destructive: [
          "bg-destructive-600 text-white shadow-sm",
          "hover:bg-destructive-700 active:bg-destructive-800",
          "dark:bg-destructive-600 dark:hover:bg-destructive-500",
        ],
        outline: [
          "border border-[hsl(var(--border))] bg-transparent shadow-sm",
          "text-foreground",
          "hover:bg-[hsl(var(--muted))] hover:text-foreground",
          "dark:border-[hsl(var(--border))] dark:hover:bg-[hsl(var(--muted))]",
        ],
        ghost: [
          "bg-transparent text-foreground",
          "hover:bg-[hsl(var(--muted))] hover:text-foreground",
          "dark:hover:bg-[hsl(var(--muted))]",
        ],
        link: [
          "bg-transparent text-primary-600 underline-offset-4",
          "hover:underline",
          "dark:text-primary-400",
        ],
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3 text-xs",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render as child element (e.g. Next.js Link) using Radix Slot */
  asChild?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
