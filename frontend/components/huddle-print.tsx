"use client";

/**
 * HuddlePrint — Print-optimized wrapper for the morning huddle.
 *
 * Adds a thin bar at the top with clinic name + date visible only when printing.
 * All child sections gain `print:break-inside-avoid` via the parent wrapper class.
 *
 * Usage:
 *   <HuddlePrint clinicName="Clínica Sonrisa">
 *     {huddleContent}
 *   HuddlePrint>
 */

import * as React from "react";
import { cn } from "@/lib/utils";

interface HuddlePrintProps {
  clinicName?: string;
  children: React.ReactNode;
  className?: string;
}

export function HuddlePrint({ clinicName, children, className }: HuddlePrintProps) {
  const today = React.useMemo(
    () =>
      new Intl.DateTimeFormat("es-419", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      }).format(new Date()),
    [],
  );

  return (
    <div className={cn("huddle-print-root", className)}>
      {/* Print-only header */}
      <div className="hidden print:flex print:items-center print:justify-between print:border-b print:border-gray-300 print:pb-2 print:mb-4">
        {clinicName && (
          <span className="text-sm font-semibold text-gray-800">{clinicName}</span>
        )}
        <span className="text-sm text-gray-600 capitalize">{today}</span>
        <span className="text-xs text-gray-500">Morning Huddle</span>
      </div>

      {/* Content — each direct child section avoids page breaks */}
      <div className="space-y-6 print:space-y-4 [&>*]:print:break-inside-avoid">
        {children}
      </div>

      {/* Print-only footer */}
      <div className="hidden print:block print:border-t print:border-gray-300 print:pt-2 print:mt-6">
        <p className="text-xs text-gray-400 text-center">
          DentalOS — Documento generado el {today}. Uso interno.
        </p>
      </div>

      {/* Global print styles injected via a style tag */}
      <style
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{
          __html: `
@media print {
  @page { margin: 1.5cm; }
  body { font-size: 11pt; }
  .huddle-print-root { color: #111; }
  .huddle-print-root a { color: #111 !important; text-decoration: none !important; }
  .huddle-print-root button { display: none !important; }
  .huddle-print-root [data-print-hide] { display: none !important; }
}
          `,
        }}
      />
    </div>
  );
}
