"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PaginationProps {
  /** Current page number (1-indexed) */
  page: number;
  /** Number of items per page */
  pageSize: number;
  /** Total number of items across all pages */
  total: number;
  /** Called with the new page number when user navigates */
  onChange: (page: number) => void;
  /** Max number of page buttons to show (default: 5) */
  maxVisible?: number;
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildPageRange(current: number, total: number, maxVisible: number): Array<number | "ellipsis"> {
  if (total <= maxVisible) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const half = Math.floor(maxVisible / 2);
  let start = Math.max(1, current - half);
  let end = start + maxVisible - 1;

  if (end > total) {
    end = total;
    start = Math.max(1, end - maxVisible + 1);
  }

  const pages: Array<number | "ellipsis"> = [];

  if (start > 1) {
    pages.push(1);
    if (start > 2) pages.push("ellipsis");
  }

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (end < total) {
    if (end < total - 1) pages.push("ellipsis");
    pages.push(total);
  }

  return pages;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Pagination({
  page,
  pageSize,
  total,
  onChange,
  maxVisible = 5,
  className,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // Clamp current page to valid range
  const safePage = Math.min(Math.max(1, page), totalPages);

  const firstItem = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const lastItem = Math.min(safePage * pageSize, total);

  const pages = buildPageRange(safePage, totalPages, maxVisible);

  function goTo(p: number) {
    if (p < 1 || p > totalPages || p === safePage) return;
    onChange(p);
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 sm:flex-row sm:justify-between",
        className,
      )}
      aria-label="Paginación"
    >
      {/* Count display */}
      <p className="text-sm text-[hsl(var(--muted-foreground))] shrink-0">
        {total === 0 ? (
          "Sin resultados"
        ) : (
          <>
            Mostrando{" "}
            <span className="font-medium text-foreground">
              {firstItem}–{lastItem}
            </span>{" "}
            de{" "}
            <span className="font-medium text-foreground">{total}</span>
          </>
        )}
      </p>

      {/* Page controls */}
      {totalPages > 1 && (
        <nav className="flex items-center gap-1" aria-label="Páginas">
          {/* Previous */}
          <Button
            variant="outline"
            size="icon"
            onClick={() => goTo(safePage - 1)}
            disabled={safePage <= 1}
            aria-label="Página anterior"
            className="h-8 w-8"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {/* Page numbers */}
          {pages.map((p, idx) => {
            if (p === "ellipsis") {
              return (
                <span
                  key={`ellipsis-${idx}`}
                  className="flex h-8 w-8 items-center justify-center text-[hsl(var(--muted-foreground))]"
                  aria-hidden="true"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </span>
              );
            }

            const isActive = p === safePage;
            return (
              <button
                key={p}
                type="button"
                onClick={() => goTo(p)}
                disabled={isActive}
                aria-label={`Página ${p}`}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-md text-sm font-medium",
                  "transition-colors duration-150",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
                  "disabled:pointer-events-none",
                  isActive
                    ? "bg-primary-600 text-white shadow-sm"
                    : "text-foreground border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]",
                )}
              >
                {p}
              </button>
            );
          })}

          {/* Next */}
          <Button
            variant="outline"
            size="icon"
            onClick={() => goTo(safePage + 1)}
            disabled={safePage >= totalPages}
            aria-label="Página siguiente"
            className="h-8 w-8"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </nav>
      )}
    </div>
  );
}
