"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Download, FileText, Send } from "lucide-react";

function getEInvoiceStatusBadge(status: string) {
  switch (status) {
    case "pending":
      return <Badge variant="outline">Pendiente</Badge>;
    case "submitted":
      return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">Enviada</Badge>;
    case "accepted":
      return <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">Aceptada</Badge>;
    case "rejected":
      return <Badge variant="destructive">Rechazada</Badge>;
    case "error":
      return <Badge variant="destructive">Error</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export default function EInvoicesPage() {
  // Placeholder — in production, this would list e-invoices
  // For now, show an informational card
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Facturación Electrónica DIAN</CardTitle>
          <CardDescription>
            Envío de facturas electrónicas a la DIAN vía MATIAS
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <FileText className="mx-auto h-12 w-12 text-[hsl(var(--muted-foreground))] mb-4" />
            <h3 className="text-lg font-medium mb-2">
              Facturación electrónica disponible
            </h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] max-w-md mx-auto">
              Para enviar una factura electrónica, vaya a Facturación, seleccione una factura
              y use el botón "Enviar a DIAN". Las facturas enviadas aparecerán aquí.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Status legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Estados de factura electrónica</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("pending")}
              <span className="text-sm">En procesamiento</span>
            </div>
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("submitted")}
              <span className="text-sm">Enviada a DIAN</span>
            </div>
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("accepted")}
              <span className="text-sm">Aceptada por DIAN</span>
            </div>
            <div className="flex items-center gap-2">
              {getEInvoiceStatusBadge("rejected")}
              <span className="text-sm">Rechazada por DIAN</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
