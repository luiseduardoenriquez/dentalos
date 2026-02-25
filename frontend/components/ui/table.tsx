"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Table Wrapper ────────────────────────────────────────────────────────────

/**
 * Outer wrapper that provides horizontal scroll on overflow.
 * Always wrap Table with this on mobile.
 */
const TableWrapper = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("relative w-full overflow-x-auto", className)}
      {...props}
    />
  ),
);
TableWrapper.displayName = "TableWrapper";

// ─── Table ────────────────────────────────────────────────────────────────────

const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <table
      ref={ref}
      className={cn("w-full caption-bottom text-sm", className)}
      {...props}
    />
  ),
);
Table.displayName = "Table";

// ─── TableHeader ──────────────────────────────────────────────────────────────

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />
));
TableHeader.displayName = "TableHeader";

// ─── TableBody ────────────────────────────────────────────────────────────────

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn(
      "[&_tr:last-child]:border-0",
      // Optional striping: add data-striped="true" on TableBody
      "data-[striped=true]:[&_tr:nth-child(even)]:bg-[hsl(var(--muted))/30]",
      className,
    )}
    {...props}
  />
));
TableBody.displayName = "TableBody";

// ─── TableFooter ──────────────────────────────────────────────────────────────

const TableFooter = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={cn(
      "border-t border-[hsl(var(--border))] bg-[hsl(var(--muted))]/50 font-medium",
      "[&>tr]:last:border-b-0",
      className,
    )}
    {...props}
  />
));
TableFooter.displayName = "TableFooter";

// ─── TableRow ─────────────────────────────────────────────────────────────────

const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      "border-b border-[hsl(var(--border))] transition-colors",
      "hover:bg-[hsl(var(--muted))]/50",
      "data-[state=selected]:bg-[hsl(var(--muted))]",
      className,
    )}
    {...props}
  />
));
TableRow.displayName = "TableRow";

// ─── TableHead ────────────────────────────────────────────────────────────────

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      "h-11 px-4 text-left align-middle",
      "text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide",
      "[&:has([role=checkbox])]:pr-0",
      className,
    )}
    {...props}
  />
));
TableHead.displayName = "TableHead";

// ─── TableCell ────────────────────────────────────────────────────────────────

const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn(
      "px-4 py-3 align-middle text-sm",
      "[&:has([role=checkbox])]:pr-0",
      className,
    )}
    {...props}
  />
));
TableCell.displayName = "TableCell";

// ─── TableCaption ─────────────────────────────────────────────────────────────

const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={cn("mt-4 text-sm text-[hsl(var(--muted-foreground))]", className)}
    {...props}
  />
));
TableCaption.displayName = "TableCaption";

export {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
};
