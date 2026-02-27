"use client";

import { MessageSquare, Calendar, CreditCard, FileText, Mail, Lock, ExternalLink } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/hooks/use-auth";
import { cn } from "@/lib/utils";

// ─── Integration Card ────────────────────────────────────────────────────────

interface IntegrationCardProps {
  name: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  status: "configured" | "not_configured" | "coming_soon";
  statusLabel: string;
  onConfigure?: () => void;
}

function IntegrationCard({
  name,
  description,
  icon: Icon,
  iconColor,
  iconBg,
  status,
  statusLabel,
  onConfigure,
}: IntegrationCardProps) {
  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
              iconBg,
            )}
          >
            <Icon className={cn("h-5 w-5", iconColor)} />
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base">{name}</CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full",
              status === "configured" &&
                "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400",
              status === "not_configured" &&
                "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400",
              status === "coming_soon" &&
                "bg-muted text-muted-foreground",
            )}
          >
            {status === "configured" && (
              <span className="h-1.5 w-1.5 rounded-full bg-success-500" />
            )}
            {status === "not_configured" && (
              <span className="h-1.5 w-1.5 rounded-full bg-warning-500" />
            )}
            {statusLabel}
          </span>
          {status === "not_configured" && onConfigure && (
            <Button size="sm" variant="outline" className="h-8 text-xs" onClick={onConfigure}>
              Configurar
              <ExternalLink className="h-3 w-3 ml-1" />
            </Button>
          )}
          {status === "coming_soon" && (
            <span className="text-xs text-muted-foreground">Próximamente</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Integration data ────────────────────────────────────────────────────────

const INTEGRATIONS: IntegrationCardProps[] = [
  {
    name: "WhatsApp Business",
    description:
      "Envía recordatorios de citas, confirmaciones y notificaciones a los pacientes vía WhatsApp.",
    icon: MessageSquare,
    iconColor: "text-green-600",
    iconBg: "bg-green-50 dark:bg-green-900/20",
    status: "not_configured",
    statusLabel: "No configurado",
  },
  {
    name: "Google Calendar",
    description:
      "Sincroniza las citas de la clínica con Google Calendar para visibilidad cruzada.",
    icon: Calendar,
    iconColor: "text-blue-600",
    iconBg: "bg-blue-50 dark:bg-blue-900/20",
    status: "coming_soon",
    statusLabel: "Próximamente",
  },
  {
    name: "Mercado Pago",
    description:
      "Acepta pagos en línea desde el portal de pacientes con Mercado Pago o PSE.",
    icon: CreditCard,
    iconColor: "text-sky-600",
    iconBg: "bg-sky-50 dark:bg-sky-900/20",
    status: "coming_soon",
    statusLabel: "Próximamente",
  },
  {
    name: "DIAN / MATIAS",
    description:
      "Facturación electrónica ante la DIAN a través del proveedor tecnológico MATIAS.",
    icon: FileText,
    iconColor: "text-amber-600",
    iconBg: "bg-amber-50 dark:bg-amber-900/20",
    status: "not_configured",
    statusLabel: "No configurado",
  },
  {
    name: "Correo electrónico (SendGrid)",
    description:
      "Configuración del servicio de correo para notificaciones, recordatorios y documentos.",
    icon: Mail,
    iconColor: "text-violet-600",
    iconBg: "bg-violet-50 dark:bg-violet-900/20",
    status: "configured",
    statusLabel: "Activo",
  },
];

// ─── Page ────────────────────────────────────────────────────────────────────

export default function IntegracionesPage() {
  const { has_role } = useAuth();
  const isOwner = has_role("clinic_owner");

  return (
    <div className="max-w-3xl space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Integraciones
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Conecta servicios externos para potenciar tu clínica.
        </p>
      </div>

      {/* Access restriction notice */}
      {!isOwner && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-muted px-4 py-3 text-sm text-muted-foreground">
          <Lock className="h-4 w-4 shrink-0" />
          Solo el propietario de la clínica puede configurar integraciones.
        </div>
      )}

      {/* Integration cards */}
      <div className="grid grid-cols-1 gap-4">
        {INTEGRATIONS.map((integration) => (
          <IntegrationCard key={integration.name} {...integration} />
        ))}
      </div>
    </div>
  );
}
