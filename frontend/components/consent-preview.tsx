"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ConsentPreviewProps {
  /** Server-sanitized HTML content of the consent */
  htmlContent: string;
  /** Consent status — used to determine watermark overlay */
  status: string;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Renders sanitized HTML consent content inside a print-friendly container.
 * Adds a diagonal watermark overlay for "draft" and "voided" statuses.
 * Content is server-sanitized (bleach), so dangerouslySetInnerHTML is safe here.
 */
function ConsentPreview({ htmlContent, status, className }: ConsentPreviewProps) {
  const show_watermark = status === "draft" || status === "voided";
  const watermark_text = status === "draft" ? "BORRADOR" : "ANULADO";

  return (
    <div
      className={cn(
        "relative rounded-lg border border-[hsl(var(--border))] bg-white dark:bg-[hsl(var(--card))]",
        "max-w-4xl mx-auto",
        className,
      )}
    >
      {/* ─── Watermark Overlay ─────────────────────────────────────── */}
      {show_watermark && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center overflow-hidden rounded-lg"
        >
          <span
            className={cn(
              "select-none font-black tracking-widest",
              "text-[clamp(3rem,8vw,7rem)]",
              "-rotate-45 opacity-[0.07]",
              status === "voided"
                ? "text-destructive-600 dark:text-destructive-400"
                : "text-[hsl(var(--muted-foreground))]",
            )}
          >
            {watermark_text}
          </span>
        </div>
      )}

      {/* ─── Consent Content ───────────────────────────────────────── */}
      <div
        className={cn(
          "relative z-0 px-8 py-10",
          // Typography for rendered consent HTML
          "prose prose-sm max-w-none",
          "prose-headings:font-semibold prose-headings:text-foreground",
          "prose-p:text-foreground/90 prose-p:leading-relaxed",
          "prose-ul:text-foreground/90 prose-ol:text-foreground/90",
          "prose-strong:text-foreground prose-strong:font-semibold",
          // Dark mode prose overrides
          "dark:prose-invert",
          // Print styles — ensure content renders fully in print
          "print:px-0 print:py-0",
        )}
        // Content is server-sanitized by bleach before being stored.
        // Allowed tags: b, i, u, br, p, ul, ol, li, strong, em
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: htmlContent }}
      />

      {/* ─── Print Styles ──────────────────────────────────────────── */}
      <style>{`
        @media print {
          .consent-preview-watermark {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
        }
      `}</style>
    </div>
  );
}

ConsentPreview.displayName = "ConsentPreview";

export { ConsentPreview };
