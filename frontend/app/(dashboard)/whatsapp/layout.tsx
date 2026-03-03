"use client";

import * as React from "react";

export default function WhatsAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col h-full">
      {/* Page header — breadcrumb area */}
      <div className="shrink-0 border-b border-[hsl(var(--border))] px-6 py-4">
        <h1 className="text-xl font-semibold tracking-tight">WhatsApp</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Conversaciones de WhatsApp con pacientes
        </p>
      </div>

      {/* Full-height content — let children use all available vertical space */}
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}
