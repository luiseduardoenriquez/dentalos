import type { ReactNode } from "react";

/**
 * Agenda route group layout.
 * Provides a full-height flex container for the calendar and today views.
 */
export default function AgendaLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <div className="flex flex-col h-full">{children}</div>;
}
