"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
  Eye,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ConversationViewer } from "@/components/chatbot/conversation-viewer";
import { formatDateTime, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type ConversationStatus = "active" | "escalated" | "resolved";

interface ChatbotConversation {
  id: string;
  channel: string;
  patient_name: string | null;
  patient_phone: string | null;
  status: ConversationStatus;
  last_intent: string | null;
  intent_confidence: number | null;
  started_at: string;
  updated_at: string;
  message_count: number;
}

interface ConversationListResponse {
  items: ChatbotConversation[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<ConversationStatus, string> = {
  active: "Activo",
  escalated: "Escalado",
  resolved: "Resuelto",
};

const STATUS_FILTERS: Array<{ value: ConversationStatus | "all"; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activo" },
  { value: "escalated", label: "Escalado" },
  { value: "resolved", label: "Resuelto" },
];

// ─── Channel labels ───────────────────────────────────────────────────────────

const CHANNEL_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  web: "Web",
  sms: "SMS",
};

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4, 5].map((i) => (
        <Skeleton key={i} className="h-12 w-full rounded" />
      ))}
    </div>
  );
}

// ─── Status badge ─────────────────────────────────────────────────────────────

function ConversationStatusBadge({ status }: { status: ConversationStatus }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-medium",
        status === "active" &&
          "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
        status === "escalated" &&
          "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-700",
        status === "resolved" &&
          "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
      )}
    >
      {STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ChatbotMonitorPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = React.useState(1);
  const [statusFilter, setStatusFilter] = React.useState<ConversationStatus | "all">("all");
  const [selectedConversationId, setSelectedConversationId] = React.useState<string | null>(null);
  const pageSize = 20;

  const queryKey = ["chatbot-conversations", page, pageSize, statusFilter];

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey,
    queryFn: () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (statusFilter !== "all") params.set("status", statusFilter);
      return apiGet<ConversationListResponse>(`/chatbot/conversations?${params}`);
    },
    staleTime: 30_000,
  });

  const { mutate: escalate, isPending: isEscalating } = useMutation({
    mutationFn: (id: string) => apiPost<void>(`/chatbot/conversations/${id}/escalate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chatbot-conversations"] }),
  });

  const { mutate: resolve, isPending: isResolving } = useMutation({
    mutationFn: (id: string) => apiPost<void>(`/chatbot/conversations/${id}/resolve`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chatbot-conversations"] }),
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;
  const conversations = data?.items ?? [];

  // Reset page on filter change
  React.useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Monitor de Chatbot
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Supervisa las conversaciones del asistente virtual.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isLoading && "animate-spin")} />
            Actualizar
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/chatbot/config">
              <Settings className="mr-1.5 h-3.5 w-3.5" />
              Configuración
            </Link>
          </Button>
        </div>
      </div>

      {/* ─── Filter tabs ─────────────────────────────────────────────────── */}
      <div className="flex gap-1.5 flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setStatusFilter(f.value)}
            className={cn(
              "rounded-full px-3 py-1 text-sm font-medium transition-colors",
              statusFilter === f.value
                ? "bg-primary-600 text-white"
                : "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))]/80",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ─── Conversations table ──────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary-600" />
            Conversaciones
          </CardTitle>
          <CardDescription>
            {data
              ? `${data.total.toLocaleString("es-CO")} conversación${data.total !== 1 ? "es" : ""}`
              : "Cargando..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton />
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <AlertCircle className="h-7 w-7 text-red-500" />
              <p className="text-sm text-red-600 dark:text-red-400">
                Error al cargar las conversaciones.
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Reintentar
              </Button>
            </div>
          ) : conversations.length === 0 ? (
            <p className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No hay conversaciones con ese filtro.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Canal</TableHead>
                  <TableHead>Paciente</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Última intención</TableHead>
                  <TableHead>Iniciado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conversations.map((conv) => (
                  <TableRow
                    key={conv.id}
                    className={cn(
                      conv.status === "escalated" &&
                        "bg-amber-50/50 dark:bg-amber-900/10",
                    )}
                  >
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                      {CHANNEL_LABELS[conv.channel] ?? conv.channel}
                    </TableCell>
                    <TableCell className="font-medium text-foreground text-sm">
                      {conv.patient_name ?? conv.patient_phone ?? (
                        <span className="italic text-[hsl(var(--muted-foreground))]">
                          Desconocido
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        {conv.status === "escalated" && (
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                        )}
                        <ConversationStatusBadge status={conv.status} />
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      {conv.last_intent ? (
                        <span className="text-foreground">{conv.last_intent}</span>
                      ) : (
                        <span className="italic text-[hsl(var(--muted-foreground))]">—</span>
                      )}
                      {conv.intent_confidence != null && (
                        <span className="ml-1 text-xs text-[hsl(var(--muted-foreground))]">
                          ({(conv.intent_confidence * 100).toFixed(0)}%)
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                      {formatDateTime(conv.started_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs"
                          onClick={() => setSelectedConversationId(conv.id)}
                        >
                          <Eye className="mr-1 h-3 w-3" />
                          Ver
                        </Button>
                        {conv.status === "active" && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs text-amber-600 border-amber-200 hover:bg-amber-50 dark:text-amber-400"
                            disabled={isEscalating}
                            onClick={() => escalate(conv.id)}
                          >
                            <AlertTriangle className="mr-1 h-3 w-3" />
                            Escalar
                          </Button>
                        )}
                        {(conv.status === "active" || conv.status === "escalated") && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs text-green-600 border-green-200 hover:bg-green-50 dark:text-green-400"
                            disabled={isResolving}
                            onClick={() => resolve(conv.id)}
                          >
                            <CheckCircle2 className="mr-1 h-3 w-3" />
                            Resolver
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {!isLoading && !isError && totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Anterior
              </Button>
              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                Página {page} de {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ─── Conversation viewer dialog ───────────────────────────────────── */}
      {selectedConversationId && (
        <ConversationViewer
          conversationId={selectedConversationId}
          onClose={() => setSelectedConversationId(null)}
        />
      )}
    </div>
  );
}
