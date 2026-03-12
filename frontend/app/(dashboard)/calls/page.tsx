"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Phone } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Pagination } from "@/components/pagination";
import { CallLogTable } from "@/components/calls/call-log-table";
import { useCallLogs, type CallLogResponse } from "@/lib/hooks/use-calls";

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Call log list page — shows paginated VoIP call history with direction and
 * status filters. Clicking a row opens the notes edit dialog.
 */
export default function CallsPage() {
  const router = useRouter();
  const [page, setPage] = React.useState(1);
  const [direction, setDirection] = React.useState<string>("all");
  const [status, setStatus] = React.useState<string>("all");

  const { data, isLoading } = useCallLogs(page, PAGE_SIZE, direction, status);

  const calls = data?.items ?? [];
  const total = data?.total ?? 0;

  function handleDirectionChange(value: string) {
    setDirection(value);
    setPage(1);
  }

  function handleStatusChange(value: string) {
    setStatus(value);
    setPage(1);
  }

  function handleRowClick(call: CallLogResponse) {
    router.push(`/calls/${call.id}`);
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Phone className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">
          Registro de llamadas
        </h1>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Direction filter */}
        <div className="space-y-1">
          <label
            htmlFor="calls-direction"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Dirección
          </label>
          <Select value={direction} onValueChange={handleDirectionChange}>
            <SelectTrigger id="calls-direction" className="w-40">
              <SelectValue placeholder="Todas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas</SelectItem>
              <SelectItem value="inbound">Entrantes</SelectItem>
              <SelectItem value="outbound">Salientes</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Status filter */}
        <div className="space-y-1">
          <label
            htmlFor="calls-status"
            className="text-xs font-medium text-[hsl(var(--muted-foreground))]"
          >
            Estado
          </label>
          <Select value={status} onValueChange={handleStatusChange}>
            <SelectTrigger id="calls-status" className="w-44">
              <SelectValue placeholder="Todos los estados" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los estados</SelectItem>
              <SelectItem value="completed">Completadas</SelectItem>
              <SelectItem value="missed">Perdidas</SelectItem>
              <SelectItem value="in_progress">En curso</SelectItem>
              <SelectItem value="ringing">Sonando</SelectItem>
              <SelectItem value="voicemail">Buzón de voz</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">
            {total > 0
              ? `${total} llamada${total !== 1 ? "s" : ""}`
              : "Llamadas"}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <CallLogTable
            calls={calls}
            isLoading={isLoading}
            onRowClick={handleRowClick}
          />
        </CardContent>
      </Card>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onChange={setPage}
        />
      )}

    </div>
  );
}
