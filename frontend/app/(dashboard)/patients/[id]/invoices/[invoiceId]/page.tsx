"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  Receipt,
  Send,
  DollarSign,
  CalendarDays,
  Download,
  XCircle,
  Banknote,
  CreditCard,
  ArrowLeftRight,
  HelpCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/empty-state";
import { InvoiceStatusBadge } from "@/components/billing/invoice-status-badge";
import { BalanceSummary } from "@/components/billing/balance-summary";
import { StatusTimeline } from "@/components/billing/status-timeline";
import { PaymentRecordModal } from "@/components/billing/payment-record-modal";
import { PaymentPlanModal } from "@/components/billing/payment-plan-modal";
import { InstallmentTracker } from "@/components/billing/installment-tracker";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  useInvoice,
  useSendInvoice,
  useCancelInvoice,
} from "@/lib/hooks/use-invoices";
import { usePayments, usePaymentPlan } from "@/lib/hooks/use-payments";
import type { InstallmentResponse } from "@/lib/hooks/use-payments";
import { PAYMENT_METHOD_LABELS } from "@/lib/validations/payment";
import { formatDate, formatCurrency, cn } from "@/lib/utils";

// ─── Payment Method Icon ─────────────────────────────────────────────────────

const PAYMENT_METHOD_ICONS: Record<string, React.ElementType> = {
  cash: Banknote,
  card: CreditCard,
  transfer: ArrowLeftRight,
  other: HelpCircle,
};

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function InvoiceDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-5 w-20" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-28 rounded-md" />
          <Skeleton className="h-9 w-28 rounded-md" />
        </div>
      </div>
      <Skeleton className="h-48 w-full rounded-xl" />
      <Skeleton className="h-32 w-full rounded-xl" />
      <Skeleton className="h-32 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string; invoiceId: string }>();
  const { id: patientId, invoiceId } = params;
  const searchParams = useSearchParams();
  const router = useRouter();

  const [showPaymentModal, setShowPaymentModal] = React.useState(false);
  const [showPlanModal, setShowPlanModal] = React.useState(false);
  const [showCancelDialog, setShowCancelDialog] = React.useState(false);
  const [installmentPrefill, setInstallmentPrefill] = React.useState<number | undefined>(undefined);

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: invoice, isLoading: isLoadingInvoice } = useInvoice(patientId, invoiceId);
  const { data: paymentsData } = usePayments(patientId, invoiceId);
  const { data: paymentPlan } = usePaymentPlan(patientId, invoiceId);

  const { mutate: sendInvoice, isPending: isSending } = useSendInvoice(patientId, invoiceId);
  const { mutate: cancelInvoice, isPending: isCancelling } = useCancelInvoice(patientId, invoiceId);

  const isLoading = isLoadingPatient || isLoadingInvoice;
  const autoSendFired = React.useRef(false);

  // Auto-send when navigated with ?send=true (e.g. from "Guardar y enviar")
  React.useEffect(() => {
    if (
      searchParams.get("send") === "true" &&
      invoice?.status === "draft" &&
      !isSending &&
      !autoSendFired.current
    ) {
      autoSendFired.current = true;
      sendInvoice(undefined, {
        onSettled: () => {
          router.replace(`/patients/${patientId}/invoices/${invoiceId}`);
        },
      });
    }
  }, [searchParams, invoice?.status, isSending, sendInvoice, router, patientId, invoiceId]);
  const payments = paymentsData?.items ?? [];

  function handlePayInstallment(installment: InstallmentResponse) {
    setInstallmentPrefill(installment.amount);
    setShowPaymentModal(true);
  }

  function handleOpenPayment() {
    setInstallmentPrefill(undefined);
    setShowPaymentModal(true);
  }

  if (isLoading) {
    return <InvoiceDetailSkeleton />;
  }

  if (!patient || !invoice) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Factura no encontrada"
        description="La factura que buscas no existe o no tienes permiso para verla."
        action={{
          label: "Volver a facturas",
          href: `/patients/${patientId}/invoices`,
        }}
      />
    );
  }

  const canSend = ["draft", "sent", "overdue"].includes(invoice.status);
  const canPay = ["sent", "overdue", "partial"].includes(invoice.status);
  const canCreatePlan = ["sent", "overdue"].includes(invoice.status) && !paymentPlan && invoice.balance > 0;
  const canCancel = !["cancelled", "paid"].includes(invoice.status);

  return (
    <>
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
            className="hover:text-foreground transition-colors truncate max-w-[130px]"
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
          <span className="text-foreground font-mono font-medium">
            {invoice.invoice_number}
          </span>
        </nav>

        {/* ─── Header Card ─────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between rounded-xl border border-[hsl(var(--border))] p-5 bg-[hsl(var(--card))]">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <Receipt className="h-5 w-5 text-primary-600" />
              <h1 className="text-xl font-bold text-foreground font-mono">
                {invoice.invoice_number}
              </h1>
              <InvoiceStatusBadge status={invoice.status} />
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[hsl(var(--muted-foreground))]">
              <span>
                Creada el{" "}
                <span className="font-medium text-foreground">
                  {formatDate(invoice.created_at)}
                </span>
              </span>
              {invoice.due_date && (
                <span>
                  Vence el{" "}
                  <span
                    className={cn(
                      "font-medium",
                      invoice.days_until_due !== null && invoice.days_until_due < 0
                        ? "text-red-600"
                        : "text-foreground",
                    )}
                  >
                    {formatDate(invoice.due_date)}
                  </span>
                </span>
              )}
              {invoice.paid_at && (
                <span>
                  Pagada el{" "}
                  <span className="font-medium text-green-600">
                    {formatDate(invoice.paid_at)}
                  </span>
                </span>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2">
            {canSend && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => sendInvoice()}
                disabled={isSending}
              >
                <Send className="mr-1.5 h-3.5 w-3.5" />
                {isSending ? "Enviando..." : "Enviar"}
              </Button>
            )}
            {canPay && (
              <Button size="sm" onClick={handleOpenPayment}>
                <DollarSign className="mr-1.5 h-3.5 w-3.5" />
                Registrar pago
              </Button>
            )}
            {canCreatePlan && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowPlanModal(true)}
              >
                <CalendarDays className="mr-1.5 h-3.5 w-3.5" />
                Plan de pagos
              </Button>
            )}
            <Button variant="outline" size="sm">
              <Download className="mr-1.5 h-3.5 w-3.5" />
              PDF
            </Button>
            {canCancel && (
              <Button
                variant="outline"
                size="sm"
                className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                onClick={() => setShowCancelDialog(true)}
              >
                <XCircle className="mr-1.5 h-3.5 w-3.5" />
                Anular
              </Button>
            )}
          </div>
        </div>

        {/* ─── Status Timeline ─────────────────────────────────────────── */}
        <Card>
          <CardContent className="pt-4 pb-4">
            <StatusTimeline status={invoice.status} />
          </CardContent>
        </Card>

        {/* ─── Line Items Table ────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Detalle de servicios
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right w-[80px]">Cant.</TableHead>
                    <TableHead className="text-right w-[140px]">Precio unit.</TableHead>
                    <TableHead className="text-right w-[120px]">Descuento</TableHead>
                    <TableHead className="text-right w-[140px]">Subtotal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoice.items
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <p className="text-sm text-foreground">{item.description}</p>
                          {item.cups_code && (
                            <p className="text-xs text-[hsl(var(--muted-foreground))] font-mono">
                              CUPS: {item.cups_code}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums">
                          {item.quantity}
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums">
                          {formatCurrency(item.unit_price, "COP")}
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums text-[hsl(var(--muted-foreground))]">
                          {item.discount > 0
                            ? `−${formatCurrency(item.discount, "COP")}`
                            : "—"}
                        </TableCell>
                        <TableCell className="text-right text-sm font-medium tabular-nums">
                          {formatCurrency(item.line_total, "COP")}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableWrapper>
          </CardContent>
        </Card>

        {/* ─── Balance Summary ─────────────────────────────────────────── */}
        <BalanceSummary
          subtotal={invoice.subtotal}
          tax={invoice.tax}
          total={invoice.total}
          amountPaid={invoice.amount_paid}
          balance={invoice.balance}
        />

        {/* ─── Payments List ───────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Pagos registrados
            </CardTitle>
          </CardHeader>
          <CardContent>
            {payments.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-6">
                No hay pagos registrados para esta factura.
              </p>
            ) : (
              <div className="space-y-3">
                {payments.map((payment) => {
                  const MethodIcon = PAYMENT_METHOD_ICONS[payment.payment_method] || HelpCircle;
                  return (
                    <div
                      key={payment.id}
                      className="flex items-center gap-3 rounded-lg border border-[hsl(var(--border))] p-3"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-50 text-green-600 dark:bg-green-900/20">
                        <MethodIcon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground">
                            {PAYMENT_METHOD_LABELS[payment.payment_method] || payment.payment_method}
                          </span>
                          {payment.reference_number && (
                            <span className="text-xs text-[hsl(var(--muted-foreground))] font-mono">
                              Ref: {payment.reference_number}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">
                          {formatDate(payment.payment_date)}
                        </p>
                      </div>
                      <span className="text-sm font-semibold text-green-600 tabular-nums">
                        +{formatCurrency(payment.amount, "COP")}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ─── Installment Tracker ─────────────────────────────────────── */}
        {paymentPlan && (
          <InstallmentTracker
            patientId={patientId}
            invoiceId={invoiceId}
            onPayInstallment={handlePayInstallment}
          />
        )}

        {/* ─── Notes ───────────────────────────────────────────────────── */}
        {invoice.notes && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Notas</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-[hsl(var(--muted-foreground))] whitespace-pre-wrap">
                {invoice.notes}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* ─── Modals ──────────────────────────────────────────────────── */}
      {invoice && (
        <>
          <PaymentRecordModal
            open={showPaymentModal}
            onOpenChange={setShowPaymentModal}
            patientId={patientId}
            invoice={invoice}
            prefillAmount={installmentPrefill}
          />
          <PaymentPlanModal
            open={showPlanModal}
            onOpenChange={setShowPlanModal}
            patientId={patientId}
            invoice={invoice}
          />
        </>
      )}

      {/* ─── Cancel Confirmation Dialog ──────────────────────────────── */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Anular factura</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que deseas anular la factura{" "}
              <span className="font-mono font-medium">{invoice?.invoice_number}</span>?
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCancelDialog(false)}
              disabled={isCancelling}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                cancelInvoice(undefined, {
                  onSuccess: () => setShowCancelDialog(false),
                });
              }}
              disabled={isCancelling}
              className="min-w-[100px]"
            >
              {isCancelling ? "Anulando..." : "Anular"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
