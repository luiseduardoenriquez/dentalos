"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useForm, FormProvider } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronRight, AlertCircle, Receipt, Save, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { LineItemsEditor } from "@/components/billing/line-items-editor";
import { TotalsPanel } from "@/components/billing/totals-panel";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  useCreateInvoice,
  useSendInvoice,
} from "@/lib/hooks/use-invoices";
import type { InvoiceResponse } from "@/lib/hooks/use-invoices";
import { invoiceCreateSchema } from "@/lib/validations/invoice";

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function NewInvoiceSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      <Skeleton className="h-6 w-48" />
      <div className="space-y-4">
        <Skeleton className="h-10 w-full rounded-md" />
        <Skeleton className="h-48 w-full rounded-md" />
        <Skeleton className="h-32 w-full rounded-md" />
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function NewInvoicePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const patientId = params.id;

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { mutate: createInvoice, isPending: isCreating } = useCreateInvoice(patientId);

  const [applyIva, setApplyIva] = React.useState(false);
  const [sendAfterCreate, setSendAfterCreate] = React.useState(false);

  // Today's date in YYYY-MM-DD
  const today = new Date().toISOString().split("T")[0];
  // Default due date: 30 days from now
  const defaultDueDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];

  const methods = useForm({
    resolver: zodResolver(invoiceCreateSchema),
    defaultValues: {
      quotation_id: null,
      due_date: defaultDueDate,
      notes: "",
      items: [],
    },
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = methods;

  function onSubmit(values: Record<string, unknown>) {
    const items = (values.items as Array<{
      description: string;
      service_id?: string | null;
      cups_code?: string | null;
      quantity: number;
      unit_price_display: number; // already cents from zod transform
      discount_display: number; // already cents from zod transform
      tooth_number?: number | null;
      treatment_plan_item_id?: string | null;
      ortho_case_id?: string | null;
      ortho_visit_id?: string | null;
    }>).map((item) => ({
      description: item.description,
      service_id: item.service_id || null,
      cups_code: item.cups_code || null,
      quantity: item.quantity,
      unit_price: item.unit_price_display,
      discount: item.discount_display,
      tooth_number: item.tooth_number ?? null,
      treatment_plan_item_id: item.treatment_plan_item_id || null,
      ortho_case_id: item.ortho_case_id || null,
      ortho_visit_id: item.ortho_visit_id || null,
    }));

    createInvoice(
      {
        quotation_id: (values.quotation_id as string) || null,
        due_date: values.due_date as string,
        notes: (values.notes as string) || null,
        items,
        include_tax: applyIva,
        tax_rate: applyIva ? 1900 : 0,
      },
      {
        onSuccess: (invoice: InvoiceResponse) => {
          if (sendAfterCreate) {
            // Navigate immediately — send will be triggered from detail page
            router.push(`/patients/${patientId}/invoices/${invoice.id}?send=true`);
          } else {
            router.push(`/patients/${patientId}/invoices/${invoice.id}`);
          }
        },
      },
    );
  }

  if (isLoadingPatient) {
    return <NewInvoiceSkeleton />;
  }

  if (!patient) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Paciente no encontrado"
        description="El paciente que buscas no existe o no tienes permiso para verlo."
        action={{ label: "Volver a pacientes", href: "/patients" }}
      />
    );
  }

  return (
    <FormProvider {...methods}>
      <div className="space-y-6">
        {/* ─── Breadcrumb ──────────────────────────────────────────────── */}
        <nav
          className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
          aria-label="Ruta de navegación"
        >
          <Link href="/patients" className="hover:text-foreground transition-colors">
            Pacientes
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link
            href={`/patients/${patientId}`}
            className="hover:text-foreground transition-colors truncate max-w-[150px]"
          >
            {patient.full_name}
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link
            href={`/patients/${patientId}/invoices`}
            className="hover:text-foreground transition-colors"
          >
            Facturas
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-medium">Nueva factura</span>
        </nav>

        {/* ─── Heading ─────────────────────────────────────────────────── */}
        <div className="flex items-center gap-2">
          <Receipt className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Nueva factura
          </h1>
        </div>

        {/* ─── Form ────────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Patient info + dates */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">
                Información general
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Patient info (read-only) */}
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.3)] p-3">
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Paciente</p>
                <p className="text-sm font-medium text-foreground">{patient.full_name}</p>
                {patient.document_number && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    {patient.document_type?.toUpperCase()} {patient.document_number}
                  </p>
                )}
              </div>

              {/* Due date */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label
                    htmlFor="due-date"
                    className="text-sm font-medium text-foreground"
                  >
                    Fecha de vencimiento <span className="text-destructive">*</span>
                  </label>
                  <Input
                    id="due-date"
                    type="date"
                    min={today}
                    {...register("due_date")}
                    disabled={isCreating}
                  />
                  {errors.due_date && (
                    <p className="text-xs text-destructive">
                      {errors.due_date.message}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Line items */}
          <Card>
            <CardContent className="pt-4">
              <LineItemsEditor patientId={patientId} disabled={isCreating} />
            </CardContent>
          </Card>

          {/* Totals */}
          <TotalsPanel applyIva={applyIva} onApplyIvaChange={setApplyIva} />

          {/* Notes */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Notas</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                rows={3}
                placeholder="Observaciones de la factura (opcional)"
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                {...register("notes")}
                disabled={isCreating}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push(`/patients/${patientId}/invoices`)}
              disabled={isCreating}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="outline"
              disabled={isCreating}
              onClick={() => setSendAfterCreate(false)}
              className="min-w-[160px]"
            >
              <Save className="mr-1.5 h-3.5 w-3.5" />
              {isCreating && !sendAfterCreate ? "Guardando..." : "Guardar borrador"}
            </Button>
            <Button
              type="submit"
              disabled={isCreating}
              onClick={() => setSendAfterCreate(true)}
              className="min-w-[160px]"
            >
              <Send className="mr-1.5 h-3.5 w-3.5" />
              {isCreating && sendAfterCreate ? "Guardando..." : "Guardar y enviar"}
            </Button>
          </div>
        </form>
      </div>
    </FormProvider>
  );
}
