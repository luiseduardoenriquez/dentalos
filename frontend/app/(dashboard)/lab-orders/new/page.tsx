"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, FlaskConical } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LabOrderForm } from "@/components/lab-orders/lab-order-form";
import {
  useCreateLabOrder,
  useDentalLabs,
} from "@/lib/hooks/use-lab-orders";
import type { LabOrderCreate } from "@/lib/hooks/use-lab-orders";

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function FormSkeleton() {
  return (
    <div className="space-y-5">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="space-y-1.5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-9 w-full" />
        </div>
      ))}
      <Skeleton className="h-9 w-28" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewLabOrderPage() {
  const router = useRouter();
  const { data: labs, isLoading: labsLoading } = useDentalLabs();
  const createOrder = useCreateLabOrder();

  async function handleSubmit(data: LabOrderCreate) {
    try {
      await createOrder.mutateAsync(data);
      router.push("/lab-orders");
    } catch {
      // Error toast is handled inside the hook
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      {/* Back link + header */}
      <div className="space-y-2">
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href="/lab-orders">
            <ChevronLeft className="mr-1 h-4 w-4" />
            Volver a órdenes
          </Link>
        </Button>
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">
            Nueva orden de laboratorio
          </h1>
        </div>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Registra una nueva orden para un laboratorio dental.
        </p>
      </div>

      {/* Form card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-foreground">
            Datos de la orden
          </CardTitle>
        </CardHeader>
        <CardContent>
          {labsLoading ? (
            <FormSkeleton />
          ) : (
            <LabOrderForm
              onSubmit={handleSubmit}
              isLoading={createOrder.isPending}
              labs={labs ?? []}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
