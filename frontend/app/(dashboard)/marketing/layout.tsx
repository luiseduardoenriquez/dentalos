"use client";

import * as React from "react";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Section header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Marketing</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Gestión de campañas de email y comunicaciones masivas con pacientes.
        </p>
      </div>

      {children}
    </div>
  );
}
